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

/**
 * Information about a detected token.
 */
public interface TokenResult {

  /**
   * The start offset of the detected token.
   *
   * @return integer start offset
   */
  int getStartIndex();

  /**
   * The end offset of the detected token.
   *
   * @return integer end offset
   */
  int getEndIndex();

  /**
   * Tests whether in the given text this token result has a whitespace character following it.
   *
   * @param text the source text this token was detected from
   * @return whether the token has a whitespace character or the end of the document following it.
   */
  default boolean hasSpaceAfter(CharSequence text) {
    return text.length() == getEndIndex() || Character.isWhitespace(text.charAt(getEndIndex()));
  }

  /**
   * The text of this token.
   *
   * @param text the source text
   * @return the subSequence of the source text covered by this token.
   */
  default CharSequence text(CharSequence text) {
    return text.subSequence(getStartIndex(), getEndIndex());
  }
}
