/*
 * Copyright 2019 Regents of the University of Minnesota.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package edu.umn.biomedicus.concepts;

import edu.umn.biomedicus.common.tuples.Pair;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.kohsuke.args4j.*;
import org.kohsuke.args4j.spi.PathOptionHandler;
import org.rocksdb.Options;
import org.rocksdb.RocksDB;
import org.rocksdb.RocksDBException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.Map.Entry;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * Builds the concepts dictionary.
 * <p>
 * Usage: java edu.umn.biomedicus.concepts.ConceptDictionaryBuilder [umls installation] \
 * [tuis-of-interest file] [banned-ttys file] [outputPath]
 */
public class ConceptDictionaryBuilder {
  private static final Logger LOGGER = LoggerFactory.getLogger(ConceptDictionaryBuilder.class);

  private static final Pattern SPLITTER = Pattern.compile("\\|");

  private static final Pattern SPACE_SPLITTER = Pattern.compile(" ");

  @Argument(required = true, metaVar = "PATH/TO/UMLS", handler = PathOptionHandler.class,
      usage = "Path to UMLS installation")
  private Path umlsPath;

  @Argument(index = 1, metaVar = "PATH/TO/TUIS", handler = PathOptionHandler.class,
      usage = "Path to TUIs of interest")
  private Path tuisOfInterestFile;

  @Argument(index = 2, metaVar = "PATH/TO/BANNED_TTYS", handler = PathOptionHandler.class,
      usage = "Banned TTYs file")
  private Path bannedTtysFile;

  @Argument(index = 3, metaVar = "OUTPUT_PATH", usage = "Path to write db out to.")
  private Path dbPath;

  @Option(name = "--filtered-suis", handler = PathOptionHandler.class,
      usage = "A path to a file containing SUIs to filter out.")
  private Path filteredSuisPath = null;

  @Option(name = "--filtered-cuis", handler = PathOptionHandler.class,
      usage = "A path to a file containing CUIs to filter out.")
  private Path filteredCuisPath = null;

  @Option(name = "--filtered-sui-cuis", handler = PathOptionHandler.class,
      usage = "A path to a file containing SUI-CUI combinations to filter")
  private Path filteredSuiCuisPath;

  @Option(name = "--filtered-tuis", usage = "A path to a file containing TUIs to filter out.")
  private Path filteredTuisPath;

  public static void main(String[] args) {
    ConceptDictionaryBuilder builder = new ConceptDictionaryBuilder();
    CmdLineParser parser = new CmdLineParser(builder);
    try {
      parser.parseArgument(args);
      builder.doWork();
    } catch (CmdLineException e) {
      System.err.println(e.getLocalizedMessage());
      System.err.println("java edu.umn.biomedicus.concepts.ConceptDictionaryBuilder" + parser.printExample(OptionHandlerFilter.ALL) + " PATH/TO/UMLS PATH/TO/TUIS PATH/TO/BANNED_TTYS OUTPUT_PATH");
      parser.printUsage(System.err);
    } catch (IOException e) {
      e.printStackTrace();
    }
  }

  private void doWork() throws IOException {
    Set<SUI> filteredSuis = filteredSuisPath != null ? Files.lines(filteredSuisPath).map(SUI::new)
        .collect(Collectors.toSet()) : Collections.emptySet();
    Set<CUI> filteredCuis = filteredCuisPath != null ? Files.lines(filteredCuisPath).map(CUI::new)
        .collect(Collectors.toSet()) : Collections.emptySet();
    Set<SuiCui> filteredSuiCuis = filteredSuiCuisPath != null ? Files.lines(filteredSuiCuisPath)
        .map(Pattern.compile(",")::split)
        .map(line -> new SuiCui(new SUI(line[0]), new CUI(line[1])))
        .collect(Collectors.toSet()) : Collections.emptySet();
    Set<TUI> filteredTuis = filteredTuisPath != null ? Files.lines(filteredTuisPath).map(TUI::new)
        .collect(Collectors.toSet()) : Collections.emptySet();

    RocksDB.loadLibrary();

    if (Files.exists(dbPath)) {
      Files.deleteIfExists(dbPath.resolve("phrases"));
      Files.deleteIfExists(dbPath.resolve("lowercase"));
      Files.deleteIfExists(dbPath.resolve("norms"));
    }

    System.out.println("Loading TUIs of interest");
    Set<TUI> whitelist = Files.lines(tuisOfInterestFile).map(SPLITTER::split)
        .filter(line -> line.length >= 3)
        .map(line -> line[1])
        .map(TUI::new)
        .collect(Collectors.toSet());

    Set<String> ttyBanlist = Files.lines(bannedTtysFile).collect(Collectors.toSet());

    Path mrstyPath = umlsPath.resolve("MRSTY.RRF");
    System.out.println("Loading CUI -> TUIs map from MRSTY: " + mrstyPath);
    Map<CUI, List<TUI>> cuiToTUIs = Files.lines(mrstyPath)
        .map(SPLITTER::split)
        .map(line -> {
          CUI cui = new CUI(line[0]);
          TUI tui = new TUI(line[1]);
          List<TUI> tuis = new ArrayList<>();
          if (whitelist.contains(tui)) {
            tuis.add(tui);
            return new AbstractMap.SimpleImmutableEntry<>(cui, tuis);
          }
          return null;
        })
        .filter(Objects::nonNull)
        .collect(Collectors.toMap(Entry::getKey,
            Entry::getValue,
            (firstList, secondList) -> {
              for (TUI tui : secondList) {
                if (!firstList.contains(tui)) {
                  firstList.add(tui);
                }
              }
              return firstList;
            }));
    Path mrconsoPath = umlsPath.resolve("MRCONSO.RRF");
    System.out.println("Loading phrases and SUI -> CUIs from MRCONSO: " + mrconsoPath);
    Set<SUI> bannedSUIs = new HashSet<>();

    Map<String, Integer> sources = new HashMap<>();
    Map<SuiCui, List<Pair<Integer, String>>> suiCuiSources = new HashMap<>();

    Files.createDirectories(dbPath);
    long mrConsoTotalLines = Files.lines(mrconsoPath).count();
    int mrConsoCompletedLines = 0;

    {
      NavigableMap<String, List<ConceptRow>> phrasesMap = new TreeMap<>();
      NavigableMap<String, List<ConceptRow>> lowercaseMap = new TreeMap<>();

      try (BufferedReader bufferedReader = Files.newBufferedReader(mrconsoPath)) {
        String line;
        while ((line = bufferedReader.readLine()) != null) {
          if (++mrConsoCompletedLines % 10_000 == 0) {
            System.out.println("Read " + mrConsoCompletedLines + " of " + mrConsoTotalLines);
          }
          String[] splitLine = SPLITTER.split(line);
          CUI cui = new CUI(splitLine[0]);
          if ("ENG".equals(splitLine[1])) {
            SUI sui = new SUI(splitLine[5]);
            String obsoleteOrSuppressible = splitLine[16];
            String source = splitLine[11];
            String tty = splitLine[12];
            String code = splitLine[13];
            String phrase = splitLine[14];

            if (phrase.length() < 3) {
              continue;
            }

            if (!"N".equals(obsoleteOrSuppressible)) {
              bannedSUIs.add(sui);
              continue;
            }

            if (ttyBanlist.contains(tty)) {
              bannedSUIs.add(sui);
              continue;
            }

            if (code.length() > 12) {
              code = code.substring(0, 12);
            }

            List<TUI> tuis = cuiToTUIs.get(cui);
            if (tuis == null || tuis.size() == 0) {
              LOGGER.trace("Filtering \"{}\" because it has no interesting types", phrase);
              continue;
            }
            for (TUI tui : tuis) {
              SuiCui sc = new SuiCui(sui, cui);
              if (filteredCuis.contains(cui) || filteredTuis.contains(tui)
                  || filteredSuiCuis.contains(sc) || filteredSuis
                  .contains(sui)) {
                continue;
              }

              Integer sourceId = sources.computeIfAbsent(source, (unused) -> sources.size());

              ConceptRow value = new ConceptRow(sui, cui, tui, sourceId, code);

              multimapPut(phrasesMap, phrase, value);
              multimapPut(lowercaseMap, phrase.toLowerCase(Locale.ENGLISH), value);

              multimapPut(suiCuiSources, sc, Pair.of(sourceId, code));
            }
          }
        }
        try (Options options = new Options()) {
          options.setCreateIfMissing(true);
          options.prepareForBulkLoad();
          try (RocksDB phrases = RocksDB.open(options, dbPath.resolve("phrases").toString());
               RocksDB lowercase = RocksDB.open(options, dbPath.resolve("lowercase").toString())) {
            int wrote = 0;
            for (Entry<String, List<ConceptRow>> entry : phrasesMap.entrySet()) {
              List<ConceptRow> suiCuiTuis = entry.getValue();
              byte[] suiCuiTuiBytes = getBytes(suiCuiTuis);
              phrases.put(entry.getKey().getBytes(), suiCuiTuiBytes);
              if (++wrote % 10_000 == 0) {
                System.out.println("Wrote " + wrote + " of " + phrasesMap.size() + " phrases");
              }
            }
            wrote = 0;
            for (Entry<String, List<ConceptRow>> entry : lowercaseMap.entrySet()) {
              List<ConceptRow> suiCuiTuis = entry.getValue();
              byte[] suiCuiTuiBytes = getBytes(suiCuiTuis);
              lowercase.put(entry.getKey().getBytes(), suiCuiTuiBytes);
              if (++wrote % 10_000 == 0) {
                System.out.println("Wrote " + wrote + " of " + lowercaseMap.size() + " lowercase phrases");
              }
            }
          }
        } catch (RocksDBException e) {
          e.printStackTrace();
          return;
        }
      }
    }

    Path mrxnsPath = umlsPath.resolve("MRXNS_ENG.RRF");
    System.out.println("Loading lowercase normalized strings from MRXNS_ENG: " + mrxnsPath);

    int lineCount = 0;
    long totalLines = Files.lines(mrxnsPath).count();

    NavigableMap<String, List<ConceptRow>> map = new TreeMap<>();

    try (BufferedReader bufferedReader = Files.newBufferedReader(mrxnsPath)) {
      String line;
      while ((line = bufferedReader.readLine()) != null) {
        if (++lineCount % 10_000 == 0) {
          System.out.println("Read " + lineCount + " of " + totalLines);
        }
        Iterator<String> it = SPLITTER.splitAsStream(line).iterator();

        if ("ENG".equals(it.next())) {
          String normsLine = it.next();
          List<String> norms = Arrays.asList(SPACE_SPLITTER.split(normsLine));
          CUI cui = new CUI(it.next());
          it.next();
          SUI sui = new SUI(it.next());

          if (norms.size() < 2) {
            continue;
          }

          if (bannedSUIs.contains(sui)) {
            continue;
          }

          List<TUI> tuis = cuiToTUIs.get(cui);
          if (tuis == null || tuis.size() == 0) {
            LOGGER.trace("Filtering \"{}\" because it has no interesting types", normsLine);
            continue;
          }
          for (TUI tui : tuis) {
            SuiCui sc = new SuiCui(sui, cui);
            if (filteredCuis.contains(cui) || filteredTuis.contains(tui)
                || filteredSuiCuis.contains(sc) || filteredSuis.contains(sui)) {
              continue;
            }

            List<Pair<Integer, String>> sourceList = suiCuiSources.get(sc);
            for (Pair<Integer, String> sourceCodePair : sourceList) {
              multimapPut(map, normsLine, new ConceptRow(sui, cui, tui, sourceCodePair.first(),
                  sourceCodePair.second()));
            }
          }
        }
      }
    }

    int wrote = 0;
    try (Options options = new Options();
         RocksDB normsDb = RocksDB.open(options, dbPath.resolve("norms").toString())) {
      options.setCreateIfMissing(true);
      options.prepareForBulkLoad();
      for (Entry<String, List<ConceptRow>> entry : map.entrySet()) {
        List<ConceptRow> suiCuiTuis = entry.getValue();
        byte[] suiCuiTuiBytes = getBytes(suiCuiTuis);
        normsDb.put(entry.getKey().getBytes(), suiCuiTuiBytes);
        if (++wrote % 10_000 == 0) {
          System.out.println("Wrote " + wrote + " of " + map.size() + " norm term bags.");
        }
      }
    } catch (RocksDBException e) {
      throw new IllegalStateException(e);
    }

    try (BufferedWriter writer = Files.newBufferedWriter(dbPath.resolve("sources.txt"))) {
      sources.entrySet().stream()
          .sorted(Comparator.comparing(Entry::getValue))
          .map(Entry::getKey)
          .forEach(s -> {
            try {
              writer.write(s);
              writer.newLine();
            } catch (IOException e) {
              throw new IllegalStateException(e);
            }
          });
    }
  }

  private byte[] getBytes(List<ConceptRow> rows) {
    ByteBuffer byteBuffer = ByteBuffer.allocate(ConceptRow.NUM_BYTES * rows.size());
    for (ConceptRow row : rows) {
      byteBuffer.put(row.getBytes());
    }

    return byteBuffer.array();
  }

  private <K, V> void multimapPut(Map<K, List<V>> map, K key, V value) {
    map.compute(key, (unused, v) -> {
      if (v == null) {
        v = new ArrayList<>();
      }
      v.add(value);
      return v;
    });
  }

  private static final class SuiCui implements Comparable<SuiCui> {

    private final SUI sui;
    private final CUI cui;

    SuiCui(SUI sui, CUI cui) {
      this.sui = sui;
      this.cui = cui;
    }

    @Override
    public boolean equals(@Nullable Object o) {
      if (this == o) {
        return true;
      }
      if (o == null || getClass() != o.getClass()) {
        return false;
      }

      SuiCui suiCui = (SuiCui) o;

      if (!sui.equals(suiCui.sui)) {
        return false;
      }
      return cui.equals(suiCui.cui);

    }

    @Override
    public int hashCode() {
      int result = sui.hashCode();
      result = 31 * result + cui.hashCode();
      return result;
    }

    @Override
    public int compareTo(@NotNull SuiCui o) {
      int compare = Integer.compare(sui.identifier(), o.sui.identifier());
      if (compare != 0) return compare;
      return Integer.compare(cui.identifier(), o.cui.identifier());
    }
  }
}
