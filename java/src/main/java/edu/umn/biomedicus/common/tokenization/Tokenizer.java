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

package edu.umn.biomedicus.common.tokenization;

import org.jetbrains.annotations.NotNull;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.Objects;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * Performs tokenization on text according to penn-treebank-like word tokenization rules.
 * Doesn't split trailing periods. Splits units like 10cm. Splits dimensions like 10x14.
 *
 * <p>"Performs tokenization of text according to penn - treebank - like word tokenization rules.
 * Does n't split trailing periods. Splits units like 10 cm. Splits dimensions like 10 x 14."</p>
 *
 * <p>Usage:</p>
 * <pre>
 *   {@code
 *   String text = "An example sentence.";
 *   for (TokenResult result : Tokenizer.tokenize(text)) {
 *     CharSequence tokenText = result.text(text);
 *   }
 *   }
 * </pre>
 *
 * <p>
 *   If you want to use a different list of units than the one built in, you can supply a
 *   file path using the system property "biomedicus.tokenizer.unitsListPath". Otherwise, you can
 *   put a file "unitsList.txt" on the "edu.umn.biomedicus.tokenization" classpath, modify the
 *   existing static units using {@link #replaceUnits(List)}, {@link #removeUnit(String)}, and
 *   {@link #addUnit(String)}, or create Tokenizer with a custom units list:
 *   {@link #Tokenizer(List)}, {@link #Tokenizer(List, List)}.
 * </p>
 *
 * <p>
 *   Instances of this class are stateful do not support parallel processing. If you plan on
 *   using the stateful instance methods {@link #advance(char, int)} and {@link #finish()} use
 *   multiple instances of this class to support parallelism, otherwise use the stateless static
 *   class methods {@link #allTokens(CharSequence)} and {@link #tokenize(CharSequence)}.
 * </p>
 *
 * <p>
 *   If using {@link #advance(char, int)} and {@link #finish()} the instance is reusable.
 * </p>
 *
 * <p>
 *   Implementation details: advances one character at a time until it encounters a word separator
 *   &mdash;i.e. a whitespace character like a space, tab, or newline&mdash;then uses a set of
 *   regex-based rules to split words into multiple tokens.
 * </p>
 */
public class Tokenizer {

  private static final int MAX_ITER = 10_000;

  private static final List<String> UNITS = loadUnitsList();

  private static final Pattern MID_BREAKS = Pattern.compile(
      // math and connector symbols and punctuation (except . , ' ’ - # $), dash following anything
      // or before a letter
      "[\\p{Sm}\\p{Sk}\\p{P}&&[^.,'’\\-#$]]|(?<=[^\\p{Z}])-|-(?=[\\p{L}])"
          // comma between two characters at least one of which is not a number
          + "|(?<=[^\\p{N}]),(?=[^\\p{N}])|(?<=[^\\p{N}]),(?=[\\p{N}])|(?<=[\\p{N}]),(?=[^\\p{N}])"
  );

  private static final Pattern START_BREAKS = Pattern.compile("^[',’]");

  private static final Pattern X = Pattern.compile("[xX]");

  private static final Pattern END_BREAKS = Pattern.compile(
      "(?<=('[SsDdMm]|n't|N'T|'ll|'LL|'ve|'VE|'re|'RE|'|’|,))$"
  );

  private static final Pattern NUMBER_WORD = Pattern
      .compile("[-]?[0-9.xX]*[0-9.]++([\\p{Alpha}]++)[.]?$");

  private static final Pattern NUMBER_X = Pattern
      .compile(".*?[0-9.]*[0-9]++([xX][0-9.]*[0-9.]++)+$");

  private final StringBuilder word = new StringBuilder();

  private List<String> units;

  private int startIndex = -1;

  private List<TokenResult> results;

  /**
   * Tokenizes the text, returning a new list of all the tokens in the string. Don't change the
   * text during tokenization, this method doesn't make a protective copy.
   *
   * @param text a CharSequence to tokenize
   *
   * @return List containing all of the tokens in the text
   */
  @NotNull
  public static List<TokenResult> allTokens(@NotNull CharSequence text) {
    ArrayList<TokenResult> tokenResults = new ArrayList<>();
    for (TokenResult result : tokenize(text)) {
      tokenResults.add(result);
    }
    return tokenResults;
  }

  /**
   * Returns an iterable that creates an iterator that lazily tokenizes the text, returning the
   * tokens in the text one-by-one. Don't change the text during tokenization, this method doesn't
   * make a protective copy.
   *
   * @param text a CharSequence to tokenize
   * @return iterable that tokenizes during iteration.
   */
  @NotNull
  public static Iterable<TokenResult> tokenize(@NotNull CharSequence text) {
    if (text == null) {
      throw new IllegalArgumentException("Null text");
    }

    return () -> new Iterator<TokenResult>() {
      int index = 0;
      Iterator<TokenResult> subIt = null;
      TokenResult next = null;
      Tokenizer tokenizer = new Tokenizer();

      {
        advance();
      }

      void advance() {
        for (int i = 0; i < MAX_ITER; i++) {
          if (subIt != null && subIt.hasNext()) {
            next = subIt.next();
            return;
          }
          subIt = null;
          if (index > text.length()) {
            next = null;
            return;
          } else if (index == text.length()) {
            subIt = tokenizer.finish().iterator();
            index++;
          } else {
            List<TokenResult> results = tokenizer.advance(text.charAt(index), index++);
            subIt = results.size() > 0 ? results.iterator() : null;
          }
        }
      }

      @Override
      public boolean hasNext() {
        return next != null;
      }

      @Override
      public TokenResult next() {
        if (next == null) {
          throw new NoSuchElementException("No next token.");
        }

        TokenResult temp = next;
        advance();
        return temp;
      }
    };
  }

  /**
   * Adds a unit to the default list of units to break off the end of words. This method affects the
   * global state of this class, all instances that have been created using the default
   * {@link Tokenizer#Tokenizer()} constructor and all future instances creating any constructors,
   * use with caution.
   *
   * @param unit the unit
   */
  public static void addUnit(String unit) {
    if (!UNITS.contains(unit)) {
      UNITS.add(unit);
    }
  }

  /**
   * Removes a unit from the default list of units to break off the end of words. This method
   * affects the global state of this class, all instances that have been created using the default
   * {@link Tokenizer#Tokenizer()} constructor and all future instances creating any constructors,
   * use with caution.
   *
   * @param unit the unit
   */
  public static void removeUnit(String unit) {
    UNITS.remove(unit);
  }

  /**
   * Replaces the default list of units with a new list of units. This method
   * affects the global state of this class, all instances that have been created using the default
   * {@link Tokenizer#Tokenizer()} constructor and all future instances creating any constructors,
   * use with caution. This method is also not thread-safe, there is a possibility that any
   * currently working instances may check a (temporarily) empty units list.
   *
   * @param newUnits the new list of units
   */
  public static void replaceUnits(List<String> newUnits) {
    UNITS.clear();
    UNITS.addAll(newUnits);
  }

  private static List<String> loadUnitsList() {
    String unitListPath = System.getProperty("biomedicus.tokenizer.unitsListPath");
    if (unitListPath != null) {
      try {
        return Files.readAllLines(Paths.get(unitListPath));
      } catch (IOException ignored) {

      }
    }
    InputStream is = Tokenizer.class.getResourceAsStream("unitsList.txt");
    try (BufferedReader reader = new BufferedReader(new InputStreamReader(is))) {
      return reader.lines().collect(Collectors.toList());
    } catch (IOException e) {
      throw new IllegalStateException("Failed to load units list.", e);
    }
  }

  /**
   * Default constructor, uses the built-in global state units list.
   */
  public Tokenizer() {
    units = UNITS;
  }

  /**
   * Creates a tokenizer which splits an alternate list of units from the ends of numbers.
   *
   * @param units the units to split off the end of numbers.
   */
  public Tokenizer(List<String> units) {
    this.units = units;
  }

  /**
   * Creates a tokenizer which will split additional or less units from the ends of numbers.
   *
   * @param additionalUnits any additional units to split
   * @param ignoredUnits any units not to split
   */
  public Tokenizer(List<String> additionalUnits, List<String> ignoredUnits) {
    units = new ArrayList<>(UNITS);
    units.addAll(additionalUnits);
    units.removeAll(ignoredUnits);
  }

  /**
   * Advances the tokenizer by one token, returning any tokens finalized in a list.
   *
   * @param ch the character to advance
   * @param index the index of the character
   * @return list of any tokens created from a single "word" (text between word breaks)
   */
  @NotNull
  public List<TokenResult> advance(char ch, int index) {
    int type = Character.getType(ch);
    if (type == Character.SPACE_SEPARATOR || type == Character.LINE_SEPARATOR
        || type == Character.PARAGRAPH_SEPARATOR || type == Character.FORMAT
        || ch == '\n' || ch == '\t' || ch == '\r') {
      return breakWord();
    } else {
      if (word.length() == 0) {
        startIndex = index;
      }
      word.append(ch);
    }
    return Collections.emptyList();
  }

  /**
   * Finalizes the tokenizer, returning any tokens from the last word (if there is one) in the
   * state.
   *
   * @return list of any last tokens
   */
  @NotNull
  public List<TokenResult> finish() {
    return breakWord();
  }

  private List<TokenResult> breakWord() {
    if (word.length() == 0) {
      return Collections.emptyList();
    }

    results = new ArrayList<>();

    Matcher midMatcher = MID_BREAKS.matcher(word);
    int start = 0;
    while (midMatcher.find()) {
      if (start != midMatcher.start()) {
        breakStarts(start, midMatcher.start());
      }
      if (midMatcher.start() != midMatcher.end()) {
        addResult(midMatcher.start(), midMatcher.end());
      }
      start = midMatcher.end();
    }
    if (start != word.length()) {
      breakStarts(start, word.length());
    }

    startIndex = -1;
    word.setLength(0);
    return results;
  }

  private void breakStarts(int start, int end) {
    while (true) {
      Matcher startMatcher = START_BREAKS.matcher(word.subSequence(start, end));
      if (startMatcher.find() && startMatcher.end() != 0) {
        addResult(start, start + startMatcher.end());
        start = start + startMatcher.end();
      } else {
        if (start != end) {
          breakEnds(start, end);
        }
        break;
      }
    }
  }

  private void breakEnds(int start, int end) {
    Matcher matcher = END_BREAKS.matcher(word.subSequence(start, end));
    if (matcher.find()) {
      if (matcher.start(1) != 0) {
        breakEnds(start, start + matcher.start(1));
      }
      if (matcher.start(1) != matcher.end(1)) {
        addResult(start + matcher.start(1), start + matcher.end(1));
      }
    } else {
      breakUnitsOfTheEndsOfNumbers(start, end);
    }
  }

  private void breakUnitsOfTheEndsOfNumbers(int start, int end) {
    CharSequence tokenText = word.subSequence(start, end);
    Matcher matcher = NUMBER_WORD.matcher(tokenText);
    if (matcher.matches()) {
      String suffix = matcher.group(1);
      if (suffix != null && UNITS.contains(suffix.toLowerCase())) {
        splitNumbersByX(start, start + matcher.start(1));
        addResult(start + matcher.start(1), end);
        return;
      }
    }
    splitNumbersByX(start, end);
  }

  private void splitNumbersByX(int start, int end) {
    CharSequence tokenText = word.subSequence(start, end);
    Matcher matcher = NUMBER_X.matcher(tokenText);
    if (matcher.matches()) {
      int prev = start;
      Matcher xMatcher = X.matcher(tokenText);
      while (xMatcher.find()) {
        addResult(prev, start + xMatcher.start());
        prev = start + xMatcher.end();
        addResult(start + xMatcher.start(), prev);
      }
      if (prev != end) {
        addResult(prev, end);
      }
    } else {
      addResult(start, end);
    }
  }

  private void addResult(int start, int end) {
    if (start != end) {
      results.add(new StandardTokenResult(startIndex + start, startIndex + end));
    }
  }

  static class StandardTokenResult implements TokenResult {

    private final int startIndex;
    private final int endIndex;

    StandardTokenResult(int startIndex, int endIndex) {
      this.startIndex = startIndex;
      this.endIndex = endIndex;
    }

    public int getStartIndex() {
      return startIndex;
    }

    public int getEndIndex() {
      return endIndex;
    }

    @Override
    public boolean equals(Object o) {
      if (this == o) {
        return true;
      }
      if (o == null || getClass() != o.getClass()) {
        return false;
      }
      StandardTokenResult result = (StandardTokenResult) o;
      return startIndex == result.startIndex &&
          endIndex == result.endIndex;
    }

    @Override
    public int hashCode() {
      return Objects.hash(startIndex, endIndex);
    }
  }
}
