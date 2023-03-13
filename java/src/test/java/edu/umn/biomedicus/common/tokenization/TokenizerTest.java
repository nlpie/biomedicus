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

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

import edu.umn.biomedicus.common.tokenization.Tokenizer.StandardTokenResult;
import java.util.Arrays;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import org.junit.jupiter.api.Test;

public class TokenizerTest {

  private static final String SENTENCE = "This test's logic will confirm that the tokenizer (P.T.B.-like) is well-behaved.";

  @Test
  void testWords() {
    assertEquals(Tokenizer.allTokens(SENTENCE), Arrays.asList(
        new StandardTokenResult(0, 4),
        new StandardTokenResult(5, 9),
        new StandardTokenResult(9, 11),
        new StandardTokenResult(12, 17),
        new StandardTokenResult(18, 22),
        new StandardTokenResult(23, 30),
        new StandardTokenResult(31, 35),
        new StandardTokenResult(36, 39),
        new StandardTokenResult(40, 49),
        new StandardTokenResult(50, 51),
        new StandardTokenResult(51, 57),
        new StandardTokenResult(57, 58),
        new StandardTokenResult(58, 62),
        new StandardTokenResult(62, 63),
        new StandardTokenResult(64, 66),
        new StandardTokenResult(67, 71),
        new StandardTokenResult(71, 72),
        new StandardTokenResult(72, 80)
    ));
  }

  @Test
  void testIterator() {
    Iterator<TokenResult> iterator = Tokenizer.tokenize(SENTENCE).iterator();
    assertEquals(iterator.next(), new StandardTokenResult(0, 4));
    assertEquals(iterator.next(), new StandardTokenResult(5, 9));
    assertEquals(iterator.next(), new StandardTokenResult(9, 11));
    assertEquals(iterator.next(), new StandardTokenResult(12, 17));
    assertEquals(iterator.next(), new StandardTokenResult(18, 22));
    assertEquals(iterator.next(), new StandardTokenResult(23, 30));
    assertEquals(iterator.next(), new StandardTokenResult(31, 35));
    assertEquals(iterator.next(), new StandardTokenResult(36, 39));
    assertEquals(iterator.next(), new StandardTokenResult(40, 49));
    assertEquals(iterator.next(), new StandardTokenResult(50, 51));
    assertEquals(iterator.next(), new StandardTokenResult(51, 57));
    assertEquals(iterator.next(), new StandardTokenResult(57, 58));
    assertEquals(iterator.next(), new StandardTokenResult(58, 62));
    assertEquals(iterator.next(), new StandardTokenResult(62, 63));
    assertEquals(iterator.next(), new StandardTokenResult(64, 66));
    assertEquals(iterator.next(), new StandardTokenResult(67, 71));
    assertEquals(iterator.next(), new StandardTokenResult(71, 72));
    assertEquals(iterator.next(), new StandardTokenResult(72, 80));
    assertFalse(iterator.hasNext());
  }

  @Test
  void testDoesSplitZWSP() {
    List<TokenResult> results = Tokenizer.allTokens(
        "This sentence has some zero-width spaces.\u200b\u200b"
    );

    TokenResult tokenCandidate = results.get(results.size() - 1);
    assertEquals(tokenCandidate.getEndIndex(), 41);
  }

  @Test
  void testWordsEmptySentence() {
    List<TokenResult> list = Tokenizer.allTokens("");

    assertEquals(list.size(), 0);
  }

  @Test
  void testWordsWhitespaceSentence() {
    List<TokenResult> list = Tokenizer.allTokens("\n \t   ");

    assertEquals(list.size(), 0);
  }

  @Test
  void testDoNotSplitCommaNumbers() {
    List<TokenResult> spanList = Tokenizer.allTokens("42,000,000");

    assertEquals(spanList.size(), 1);
    assertEquals(spanList.get(0).getStartIndex(), 0);
    assertEquals(spanList.get(0).getEndIndex(), 10);
  }

  @Test
  void testSplitTrailingComma() {
    List<TokenResult> list = Tokenizer.allTokens("first,");

    assertEquals(list.size(), 2);
    assertEquals(list.get(0).getStartIndex(), 0);
    assertEquals(list.get(0).getEndIndex(), 5);
  }

  @Test
  void testSplitPercent() {
    List<TokenResult> spans = Tokenizer.allTokens("42%");

    assertEquals(spans.size(), 2);
    assertEquals(spans.get(0), new StandardTokenResult(0, 2));
    assertEquals(spans.get(1), new StandardTokenResult(2, 3));
  }

  @Test
  void testParenSplitMid() {
    List<TokenResult> spans = Tokenizer.allTokens("abc(asf");

    assertEquals(spans.size(), 3);
    assertEquals(spans.get(0), new StandardTokenResult(0, 3));
    assertEquals(spans.get(1), new StandardTokenResult(3, 4));
    assertEquals(spans.get(2), new StandardTokenResult(4, 7));
  }

  @Test
  void testSplitUnitsOffTheEnd() {
    List<TokenResult> list = Tokenizer.allTokens("2.5cm");

    assertEquals(list.size(), 2);
    assertEquals(list.get(0), new StandardTokenResult(0, 3));
    assertEquals(list.get(1), new StandardTokenResult(3, 5));
  }

  @Test
  void testSingleQuote() {
    List<TokenResult> list = Tokenizer.allTokens("'xyz");

    assertEquals(list.size(), 2);
    assertEquals(list.get(0), new StandardTokenResult(0, 1));
    assertEquals(list.get(1), new StandardTokenResult(1, 4));
  }

  @Test
  void testSplitNumbersSeparatedByX() {
    List<TokenResult> list = Tokenizer.allTokens("2x3x4");

    assertEquals(list.size(), 5);
    assertEquals(list.get(0), new StandardTokenResult(0, 1));
    assertEquals(list.get(1), new StandardTokenResult(1, 2));
    assertEquals(list.get(2), new StandardTokenResult(2, 3));
    assertEquals(list.get(3), new StandardTokenResult(3, 4));
    assertEquals(list.get(4), new StandardTokenResult(4, 5));
  }

  @Test
  void testDontSplitEndOfSentenceAM() {
    List<TokenResult> list = Tokenizer.allTokens("a.m.");

    assertEquals(list, Collections.singletonList(new StandardTokenResult(0, 4)));
  }

  @Test
  void testDontSplitCommaAfterParen() {
    List<TokenResult> list = Tokenizer.allTokens("(something), something");

    assertEquals(list, Arrays.asList(
        new StandardTokenResult(0, 1),
        new StandardTokenResult(1, 10),
        new StandardTokenResult(10, 11),
        new StandardTokenResult(11, 12),
        new StandardTokenResult(13, 22)
    ));
  }

  @Test
  void testSentenceEndNumberX() {
    List<TokenResult> list = Tokenizer.allTokens("Blah 4x4.5.");

    assertEquals(list, Arrays.asList(
        new StandardTokenResult(0, 4),
        new StandardTokenResult(5, 6),
        new StandardTokenResult(6, 7),
        new StandardTokenResult(7, 11)
    ));
  }

  @Test
  void testSentenceEndingUnit() {
    List<TokenResult> list = Tokenizer.allTokens("2.5cm.");

    assertEquals(list, Arrays.asList(
        new StandardTokenResult(0, 3),
        new StandardTokenResult(3, 6)
    ));
  }
}
