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

package edu.umn.biomedicus.common.tokenization;

import edu.umn.nlpie.mtap.model.Document;
import edu.umn.nlpie.mtap.model.GenericLabel;
import edu.umn.nlpie.mtap.model.Label;
import edu.umn.nlpie.mtap.model.TextSpan;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class WhitespaceTokenizer {
  public static final Pattern WHITESPACE_PATTERN = Pattern.compile("[;.!):,\"']?(\\s++[(\"']?|\\z)");

  private WhitespaceTokenizer() {
    throw new UnsupportedOperationException();
  }

  public static List<TextSpan> tokenize(String text) {
    return tokenize(text, new TokenFactory<TextSpan>() {
      @Override
      TextSpan createToken(int startIndex, int endIndex) {
        return new TextSpan(text, startIndex, endIndex);
      }
    });
  }

  public static List<GenericLabel> tokenize(Document document) {
    return tokenize(document.getText(), new TokenFactory<GenericLabel>() {
      @Override
      GenericLabel createToken(int startIndex, int endIndex) {
        GenericLabel token = GenericLabel.createSpan(startIndex, endIndex);
        token.setDocument(document);
        return token;
      }
    });
  }

  private static <T extends Label> List<T> tokenize(String text, TokenFactory<T> tokenFactory) {
    List<T> result = new ArrayList<>();
    Matcher matcher = WHITESPACE_PATTERN.matcher(text);
    int nextBegin = 0;
    while (matcher.find()) {
      int tokenEnd = matcher.start();
      T token = tokenFactory.createToken(nextBegin, tokenEnd);
      nextBegin = matcher.end();
      if (token.length() > 0) {
        result.add(token);
      }
    }
    if (nextBegin != text.length()) {
      result.add(tokenFactory.createToken(nextBegin, text.length()));
    }
    return result;
  }

  private static abstract class TokenFactory<T extends Label> {
    abstract T createToken(int startIndex, int endIndex);
  }
}
