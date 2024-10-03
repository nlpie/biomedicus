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

import org.jetbrains.annotations.Nullable;
import org.rocksdb.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import edu.umn.biomedicus.common.utilities.RocksToSLF4JLogger;

import java.io.Closeable;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * An implementation of {@link ConceptDictionary} that uses RocksDB as a backend.
 *
 * @since 1.8.0
 */
class RocksDbConceptDictionary implements ConceptDictionary, Closeable {
  private static final Logger LOGGER = LoggerFactory.getLogger(RocksDbConceptDictionary.class);

  private final RocksDB phrases;

  private final RocksDB lowercase;

  private final RocksDB normsDB;

  private final Map<Integer, String> sources;

  RocksDbConceptDictionary(
      RocksDB phrases,
      RocksDB lowercase,
      RocksDB normsDB,
      Map<Integer, String> sources
  ) {
    this.phrases = phrases;
    this.lowercase = lowercase;
    this.normsDB = normsDB;
    this.sources = sources;
  }

  static List<ConceptRow> toList(byte[] bytes) {
    List<ConceptRow> list = new ArrayList<>();
    ByteBuffer buffer = ByteBuffer.wrap(bytes);
    while (buffer.hasRemaining()) {
      list.add(ConceptRow.next(buffer));
    }

    return list;
  }

  public static ConceptDictionary loadModel(Path dbPath, boolean inMemory) throws RocksDBException, IOException {
    RocksDB.loadLibrary();

    try (Options options = new Options()) {
      options.setInfoLogLevel(InfoLogLevel.ERROR_LEVEL);
      options.setLogger(new RocksToSLF4JLogger(InfoLogLevel.ERROR_LEVEL, LOGGER));
      LOGGER.info("Opening concepts dictionary: {}. inMemory = {}.", dbPath, inMemory);

      RocksDB phrasesDB = RocksDB.openReadOnly(options, dbPath.resolve("phrases").toString());
      RocksDB lowercaseDB = RocksDB.openReadOnly(options, dbPath.resolve("lowercase").toString());
      RocksDB normsDB = RocksDB.openReadOnly(options, dbPath.resolve("norms").toString());
      Map<Integer, String> sources = new HashMap<>();

      Files.lines(dbPath.resolve("sources.txt")).forEach(s -> sources.put(sources.size(), s));


      if (inMemory) {
        LOGGER.info("Loading concepts phrases into memory.");
        final Map<String, List<ConceptRow>> phrases = new HashMap<>();
        dumpToMap(phrasesDB, phrases, String::new);

        LOGGER.info("Loading concepts lowercases into memory.");
        final Map<String, List<ConceptRow>> lowercasePhrases = new HashMap<>();
        dumpToMap(lowercaseDB, lowercasePhrases, String::new);

        LOGGER.info("Loading concepts norms into memory.");
        final Map<String, List<ConceptRow>> normDictionary = new HashMap<>();
        dumpToMap(normsDB, normDictionary, String::new);

        LOGGER.info("Done loading concepts into memory.");

        return new ConceptDictionary() {
          @Override
          public List<PhraseConcept> withCui(CUI cui) {
            return phrases.entrySet().stream().filter(
                e -> e.getValue().stream().anyMatch(cr -> cr.getCui().equals(cui))
            ).flatMap(
                e -> e.getValue().stream().filter(cr -> cr.getCui().equals(cui))
                    .map(cr -> new PhraseConcept(e.getKey(), cr))
            ).collect(Collectors.toList());
          }

          @Override
          public List<PhraseConcept> withWord(String word) {
            return lowercasePhrases.entrySet().stream().filter(
                e -> e.getKey().contains(word)
            ).flatMap(
                e -> e.getValue().stream().map(cr -> new PhraseConcept(e.getKey(), cr))
            ).collect(Collectors.toList());
          }

          @Override
          @Nullable
          public List<ConceptRow> forPhrase(String phrase) {
            return phrases.get(phrase);
          }

          @Override
          @Nullable
          public List<ConceptRow> forLowercasePhrase(String phrase) {
            return lowercasePhrases.get(phrase);
          }

          @Override
          @Nullable
          public List<ConceptRow> forNorms(String norms) {
            return normDictionary.get(norms);
          }

          @Override
          public String source(int identifier) {
            return sources.get(identifier);
          }
        };

      }

      LOGGER.info("Done opening concepts dictionary.");

      return new RocksDbConceptDictionary(phrasesDB, lowercaseDB, normsDB, sources);
    }
  }

  private static <T> void dumpToMap(RocksDB db, Map<T, List<ConceptRow>> suiCuiTuis,
                                    Function<byte[], T> keyMapper) {
    try (RocksIterator rocksIterator = db.newIterator()) {
      rocksIterator.seekToFirst();
      while (rocksIterator.isValid()) {
        byte[] keyBytes = rocksIterator.key();
        T key = keyMapper.apply(keyBytes);
        suiCuiTuis.put(key, RocksDbConceptDictionary.toList(rocksIterator.value()));
        rocksIterator.next();
      }
    }

    db.close();
  }

  @Override
  public List<PhraseConcept> withCui(CUI cui) {
    List<PhraseConcept> results = new ArrayList<>();
    try (RocksIterator rocksIterator = phrases.newIterator()) {
      rocksIterator.seekToFirst();
      while (rocksIterator.isValid()) {
        byte[] keyBytes = rocksIterator.key();
        String phrase = new String(keyBytes, StandardCharsets.UTF_8);
        byte[] value = rocksIterator.value();
        List<ConceptRow> concepts = toList(value);
        for (ConceptRow concept : concepts) {
          if (concept.getCui().equals(cui)) {
            results.add(new PhraseConcept(phrase, concept));
          }
        }
        rocksIterator.next();
      }
    }
    return results;
  }

  @Override
  public List<PhraseConcept> withWord(String word) {
    word = word.toLowerCase(Locale.US);
    List<PhraseConcept> results = new ArrayList<>();
    try (RocksIterator rocksIterator = lowercase.newIterator()) {
      rocksIterator.seekToFirst();
      while (rocksIterator.isValid()) {
        byte[] keyBytes = rocksIterator.key();
        String phrase = new String(keyBytes, StandardCharsets.UTF_8);
        if (phrase.contains(word)) {
          byte[] value = rocksIterator.value();
          List<ConceptRow> concepts = toList(value);
          for (ConceptRow concept : concepts) {
            PhraseConcept pc = new PhraseConcept(phrase, concept);
            results.add(pc);
            System.out.println("Found: " + pc.toString());
          }
          rocksIterator.next();
        }
      }
    }
    return results;
  }

  @Nullable
  @Override
  public List<ConceptRow> forPhrase(String phrase) {
    try {
      byte[] bytes = phrases.get(phrase.getBytes(StandardCharsets.UTF_8));
      return bytes == null ? null : toList(bytes);
    } catch (RocksDBException e) {
      throw new RuntimeException(e);
    }
  }

  @Nullable
  @Override
  public List<ConceptRow> forLowercasePhrase(String phrase) {
    try {
      byte[] bytes = lowercase.get(phrase.getBytes(StandardCharsets.UTF_8));
      return bytes == null ? null : toList(bytes);
    } catch (RocksDBException e) {
      throw new RuntimeException(e);
    }
  }

  @Nullable
  @Override
  public List<ConceptRow> forNorms(String norms) {
    try {
      byte[] bytes = normsDB.get(norms.getBytes());
      return bytes == null ? null : toList(bytes);
    } catch (RocksDBException e) {
      throw new RuntimeException(e);
    }
  }

  @Nullable
  @Override
  public String source(int identifier) {
    return sources.get(identifier);
  }

  @Override
  public void close() {
    normsDB.close();
    lowercase.close();
    phrases.close();
  }
}
