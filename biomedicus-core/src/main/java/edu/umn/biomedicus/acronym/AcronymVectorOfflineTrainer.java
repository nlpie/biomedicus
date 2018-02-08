/*
 * Copyright (c) 2018 Regents of the University of Minnesota.
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

package edu.umn.biomedicus.acronym;

import edu.umn.biomedicus.exc.BiomedicusException;
import edu.umn.biomedicus.tokenization.Token;
import edu.umn.nlpengine.AbstractTextRange;
import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.nio.file.FileVisitResult;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Scanner;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.function.Function;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.annotation.Nullable;

/**
 * Trains an AcronymVectorModel based on text.
 * Does not require the biomedicus tokenizer or other elements of the pipeline.
 *
 * Reads an AcronymExpansionsModel as previously generated by AcronymExpansionsBuilder
 * and finds co-occurrence vectors of all words and phrases corresponding to expansions in text
 *
 * Created by gpfinley on 5/25/16.
 */
public class AcronymVectorOfflineTrainer {

  public final static int DEFAULT_N_WORDS = 100000;

  private final static Logger LOGGER = LoggerFactory.getLogger(AcronymVectorOfflineTrainer.class);

  private final static String TEXTBREAK = "[^\\w\\-/]+";

  private final static Pattern initialJunk = Pattern.compile("^\\W+");

  private final static Pattern finalJunk = Pattern.compile("\\W+$");

  // Stop counting words after so many bytes (should have a good idea of the top nWords by this point)
  private static final long maxBytesToCountWords = 5000000000L;

  final AcronymExpansionsModel aem;

  private final Map<String, Set<String>> alternateFormOf;

  // Only use these most common words
  private final int nWords;

  @Nullable
  WordVectorSpace vectorSpace;

  private boolean ignoreDoubleAlternates = false;

  @Nullable
  private Map<String, SparseVector> senseVectors;

  @Nullable
  private Map<String, Integer> wordFrequency;

  private long bytesWordCounted = 0;

  // Directed graph that contains all phrases and is used
  @Nullable
  private PhraseGraph phraseGraph;

  private long total = 0;

  private long visited = 0;

  /**
   * Initialize the trainer: read in possible acronym expansions
   *
   * @param expansionsFile a plaintext AcronymExpansionsModel (as created by
   * AcronymExpansionsBuilder)
   */
  public AcronymVectorOfflineTrainer(String expansionsFile, int nWords,
      @Nullable String alternateLongformsFile) throws BiomedicusException, IOException {
    this.nWords = nWords;
    // Get all possible acronym expansions and make vectors for each one
    aem = new AcronymExpansionsModel.Loader(Paths.get(expansionsFile)).loadModel();
    Set<String> allExpansions = new HashSet<>();
    for (String acronym : aem.getAcronyms()) {
      Collection<String> expansions = aem.getExpansions(acronym);
      if (expansions != null && expansions.size() > 1) {
        allExpansions.addAll(expansions);
      }
    }
    LOGGER.info(allExpansions.size() + " possible acronym expansions/senses");
    senseVectors = new TreeMap<>();
    for (String expansion : allExpansions) {
      senseVectors.put(expansion, new SparseVector());
    }

    // Get alternate forms from a separate file, if provided.
    alternateFormOf = new HashMap<>();
    if (alternateLongformsFile != null) {
      Set<String> doublyReferencedAlternateForms = new HashSet<>();
      BufferedReader alternateFormReader = new BufferedReader(
          new FileReader(alternateLongformsFile));
      LOGGER.info("Adding expansion phrase search equivalents");
      String line;
      while ((line = alternateFormReader.readLine()) != null) {
        String[] fields = line.split("\\t");
        if (senseVectors.containsKey(fields[0])) {
          for (int i = 1; i < fields.length; i++) {
            if (alternateFormOf.containsKey(fields[i])
                && !alternateFormOf.get(fields[i]).equals(Collections.singleton(fields[0]))) {
              doublyReferencedAlternateForms.add(fields[i]);
              if (ignoreDoubleAlternates) {
                LOGGER.warn(String
                    .format("%s appears as an alternate for multiple longforms; ignoring",
                        fields[i]));
              }
            } else if (senseVectors.containsKey(fields[i])) {
              if (ignoreDoubleAlternates) {
                LOGGER.warn(String.format(
                    "%s appears as a sense and as an alternate form for another sense; ignoring alternate form use",
                    fields[i]));
              } else {
                alternateFormOf.get(fields[i]).add(fields[0]);
              }
            } else {
              alternateFormOf.put(fields[i], Collections.singleton(fields[0]));
            }
          }
        } else {
          LOGGER.warn("Trying to add alternate forms of \"" + fields[0]
              + "\", which is not a known sense of any abbreviation");
        }
      }
      if (ignoreDoubleAlternates) {
        doublyReferencedAlternateForms.forEach(alternateFormOf::remove);
      }
      allExpansions.addAll(alternateFormOf.keySet());
    }
    LOGGER.info(allExpansions.size() + " possible senses, counting equivalents");

    // Build a graph that contains all possible phrases
    phraseGraph = new PhraseGraph(allExpansions, this::tokenize);
  }

  public static void main(String[] args) throws BiomedicusException, IOException {
    String expansionsFile = args[0];
    String corpusPath = args[1];
    String outDir = args.length > 2 ? args[2] : ".";
    int nWords = args.length > 3 ? Integer.parseInt(args[3]) : DEFAULT_N_WORDS;
    String alternateLongformsFile = args.length > 4 ? args[4] : null;
    AcronymVectorOfflineTrainer trainer = new AcronymVectorOfflineTrainer(expansionsFile, nWords,
        alternateLongformsFile);
    trainer.countDocuments(corpusPath);
    trainer.trainOnCorpus(corpusPath);
    trainer.writeAcronymModel(outDir);
  }

  private void countDocuments(String corpusPath) throws IOException {
    total = Files.walk(Paths.get(corpusPath)).count();
  }

  /**
   * Calculate word co-occurrence vectors from a corpus
   * Will perform a prior pass on the corpus to get word counts if that has not already been done
   *
   * @param corpusPath path to a single file or directory (in which case all files will be visited
   * recursively)
   */
  public void trainOnCorpus(String corpusPath) throws IOException {
    if (vectorSpace == null) {
      precountWords(corpusPath);
    }
    visited = 0;
    Files.walkFileTree(Paths.get(corpusPath), new FileVectorizer(true));
  }

  /**
   * Get total word counts from a corpus before training co-occurrence vectors
   *
   * @param corpusPath path to a single file or directory (in which case all files will be visited
   * recursively)
   */
  public void precountWords(String corpusPath) throws IOException {

    vectorSpace = new WordVectorSpace();
    wordFrequency = new HashMap<>();

    visited = 0;
    Files.walkFileTree(Paths.get(corpusPath), new FileVectorizer(false));

    TreeSet<String> sortedWordFreq = new TreeSet<>(new ByValue<>(wordFrequency));
    sortedWordFreq.addAll(wordFrequency.keySet());
    Map<String, Integer> dictionary = new HashMap<>();
    Iterator<String> iter = sortedWordFreq.descendingIterator();
    for (int i = 0; i < nWords; i++) {
      if (!iter.hasNext()) {
        break;
      }
      String word = iter.next();
      dictionary.put(word, i);
    }
    vectorSpace.setDictionary(dictionary);
  }

  /**
   * Finalize vectors and write model Will apply square-rooting, normalization (the operations also
   * performed by AcronymVectorModelTrainer)
   *
   * @param outFile file to serialize vectors to
   */
  public void writeAcronymModel(String outFile) throws IOException {

    assert vectorSpace != null;

    assert senseVectors != null;

    vectorSpace.buildIdf();
    SparseVector idf = vectorSpace.getIdf();
    LOGGER.info("Creating vectors for senses");
    // Create SparseVectors out of the Integer->Double maps
    for (Map.Entry<String, SparseVector> e : senseVectors.entrySet()) {
      SparseVector vector = e.getValue();
      vector.applyOperation(Math::sqrt);
      vector.multiply(idf);
      vector.normVector();
      vector.multiply(idf);
      vector.multiply(idf);
    }
    LOGGER.info(senseVectors.size() + " vectors total");
    LOGGER.info("initializing acronym vector model");
    AcronymVectorModel avm = new AcronymVectorModel(vectorSpace, null, aem, null, 0.0d);
    // can help to do the GC before trying to serialize a big model

    LOGGER.info("writing acronym vector model");
    Path outPath = Paths.get(outFile);
    avm.writeToDirectory(outPath, senseVectors);
  }

  /**
   * Simple tokenizer. Quicker than instantiating a pipeline.
   */
  private String[] tokenize(String orig) {
    orig = initialJunk.matcher(orig).replaceFirst("");
    orig = finalJunk.matcher(orig).replaceFirst("");
    return orig.toLowerCase().split(TEXTBREAK);
  }

  /**
   * Given a sense, its context, and its position in that context, add its surroundings to its
   * context vector This step constitutes reading a 'document' for the purposes of IDF
   *
   * @param expansion the expansion string, which needs to match the expansions in the sense vector
   * map
   * @param words context words
   * @param startPos array offset containing the beginning of the expansion word or phrase
   * @param endPos array offset one after the end of the expansion (always >= startPos + 1)
   */
  private void vectorizeForWord(String expansion, List<Token> words, int startPos, int endPos) {
    assert vectorSpace != null;

    assert senseVectors != null;

    SparseVector vec = vectorSpace.vectorize(words, startPos, endPos);
    senseVectors.get(expansion).add(vec);
  }

  /**
   * Go through a text file or chunk of text and vectorize for all found senses.
   */
  private void vectorizeChunk(String context) {
    assert phraseGraph != null;

    List<Token> words = Arrays.stream(tokenize(context)).map(DummyToken::new)
        .collect(Collectors.toList());
    for (int i = 0; i < words.size(); i++) {
      String result = phraseGraph.getLongestPhraseFrom(words, i);
      if (result != null) {
        Set<String> fullPhrases = alternateFormOf
            .getOrDefault(result, Collections.singleton(result));
        for (String fullPhrase : fullPhrases) {
          vectorizeForWord(fullPhrase, words, i, i + tokenize(result).length);
        }
      }
    }
  }

  /**
   * Go through a chunk of text and count all the words in it
   */
  private void countChunk(String context) {
    assert wordFrequency != null;

    String[] words = tokenize(context);
    for (String word : words) {
      Integer oldVal = wordFrequency.putIfAbsent(word, 1);
      if (oldVal != null) {
        wordFrequency.put(word, oldVal + 1);
      }
    }
  }

  class PhraseGraph {

    private final Map<String, Object> graph;

    @SuppressWarnings("unchecked")
    public PhraseGraph(Iterable<String> phrases, Function<String, String[]> tokenizer) {
      graph = new HashMap<>();
      for (String phrase : phrases) {
        List<String> words = new ArrayList<>(Arrays.asList(tokenizer.apply(phrase)));
        Map<String, Object> addToThisMap = graph;
        while (true) {
          String firstWord = words.get(0);
          addToThisMap.putIfAbsent(firstWord, new HashMap<String, Map>());
          addToThisMap = (Map) addToThisMap.get(firstWord);
          words.remove(0);
          if (words.size() == 0) {
            addToThisMap.put(null, phrase);
            break;
          }
        }
      }
    }

    /**
     * @param words a list of tokens
     * @param index the index to start looking in that list
     * @return the longest possible phrase, or null if none found from this index
     */
    @Nullable
    @SuppressWarnings("unchecked")
    public String getLongestPhraseFrom(List<Token> words, int index) {
      String longestEligiblePhrase = null;
      Map<String, Object> lookup = graph;
      for (int i = index; i < words.size(); i++) {
        String thisWord = words.get(i).getText();
        if (lookup.containsKey(null)) {
          longestEligiblePhrase = (String) lookup.get(null);
        }
        if (lookup.containsKey(thisWord)) {
          lookup = (Map) lookup.get(thisWord);
        } else {
          break;
        }
      }
      return longestEligiblePhrase;
    }
  }

  private class DummyToken extends AbstractTextRange implements Token {

    private String text;

    DummyToken(String text) {
      super(0, 0);
      this.text = text;
    }

    @Override
    public String getText() {
      return text;
    }

    @Override
    public boolean getHasSpaceAfter() {
      return true;
    }
  }

  /**
   * For visiting multiple files under the same path, vectorizing or counting the words in each
   */
  private class FileVectorizer extends SimpleFileVisitor<Path> {

    private boolean vectorizeNotCount;

    FileVectorizer(boolean vectorizeNotCount) {
      this.vectorizeNotCount = vectorizeNotCount;
    }

    @Override
    public FileVisitResult visitFile(Path file, BasicFileAttributes attr) throws IOException {
      if (file.getFileName().toString().startsWith(".")) {
        return FileVisitResult.CONTINUE;
      }
      // Files that are larger than 100 MB should not be read all at once
      if (file.toFile().length() < 100000000) {
        Scanner scanner = new Scanner(file.toFile()).useDelimiter("\\Z");
        String fileText = scanner.next();
        scanner.close();
        if (vectorizeNotCount) {
          vectorizeChunk(fileText);
        } else {
          countChunk(fileText);
          bytesWordCounted += fileText.length();
          if (bytesWordCounted >= maxBytesToCountWords) {
            LOGGER.info("Done counting words.");
            return FileVisitResult.TERMINATE;
          }
        }
      } else {
        // Make virtual files out of this file, splitting on whitespace every ~10 MB
        BufferedReader reader = new BufferedReader(new FileReader(file.toFile()));
        char[] chunk = new char[10000000];
        long totalLength = 0;
        while (reader.read(chunk) > 0) {
          StringBuilder lineBuilder = new StringBuilder(new String(chunk));
          while (true) {
            // This could be sped up--reading bytes one at a time is fantastically slow
            int nextByte = reader.read();
            char nextChar = (char) nextByte;
            if (nextByte < 0 || nextChar == ' ' || nextChar == '\t' || nextChar == '\n') {
              break;
            }
            lineBuilder.append((char) nextByte);
          }
          String line = lineBuilder.toString();
          totalLength += line.length();
          if (vectorizeNotCount) {
            vectorizeChunk(line);
          } else {
            countChunk(line);
            LOGGER.info(wordFrequency.size() + " total words found");
            bytesWordCounted += line.length();
            if (bytesWordCounted >= maxBytesToCountWords) {
              LOGGER.info("Done counting words.");
              return FileVisitResult.TERMINATE;
            }
          }
          LOGGER.info(totalLength + " bytes of large file " + file + " processed");
        }
        reader.close();
      }

      LOGGER.trace(file + " visited");

      visited++;
      if (visited % 1000 == 0) {
        LOGGER.info("Visited {} of {}", visited, total);
      }

      return FileVisitResult.CONTINUE;
    }
  }

  /**
   * General-use Comparator for sorting based on map values
   * Be sure that the values are Comparable (will probably be Integer or Double)
   * Created by gpfinley on 3/1/16.
   */
  public class ByValue<K extends Comparable<K>, V extends Comparable<V>> implements Comparator<K> {

    private Map<K, V> map;

    public ByValue(Map<K, V> map) {
      this.map = map;
    }

    @Override
    public int compare(K o1, K o2) {
      V v1 = map.get(o1);
      V v2 = map.get(o2);
      if (v1 == v2) {
        return 0;
      }
      int cmp = v1.compareTo(v2);
      if (cmp != 0) return cmp;
      return o1.compareTo(o2);
    }
  }

}
