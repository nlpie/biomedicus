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

import edu.umn.nlpnewt.model.GenericLabel;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class WhitespaceTokenizer {
  public static final Pattern WHITESPACE_PATTERN = Pattern.compile("[;.!):,\"']?(\\s++[(\"']?|\\z)");

  private WhitespaceTokenizer() {
    throw new UnsupportedOperationException();
  }

  public static List<GenericLabel> tokenize(CharSequence text) {
    List<GenericLabel> result = new ArrayList<>();
    Matcher matcher = WHITESPACE_PATTERN.matcher(text);
    int nextBegin = 0;
    while (matcher.find()) {
      int tokenEnd = matcher.start();
      GenericLabel token = GenericLabel.createSpan(nextBegin, tokenEnd);
      nextBegin = matcher.end();
      if (token.length() > 0) {
        result.add(token);
      }
    }
    if (nextBegin != text.length()) {
      result.add(GenericLabel.createSpan(nextBegin, text.length()));
    }
    return result;
  }
}
