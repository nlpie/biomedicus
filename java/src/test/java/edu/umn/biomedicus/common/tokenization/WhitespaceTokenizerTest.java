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
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.assertEquals;

class WhitespaceTokenizerTest {
  @Test
  void testWhitespaceTokenizer() {
    String text = "The quick-brown-fox jumps, over the lazy dog.";
    List<GenericLabel> tokenize = WhitespaceTokenizer.tokenize(text);
    List<String> list = tokenize.stream().map(t -> t.coveredText(text).toString()).collect(Collectors.toList());
    assertEquals(Arrays.asList("The", "quick-brown-fox", "jumps", "over", "the", "lazy", "dog"), list);
  }
}
