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

import edu.umn.nlpnewt.model.GenericLabel;

import java.util.List;
import java.util.Set;

/**
 * Describes any generic acronym detection and normalization model
 * The essential capabilities of the model are
 * 1) to determine if something is an acronym, and
 * 2) to expand a given acronym Token given its context Tokens
 * Models are generally serializable as well so they can be trained ahead of time
 */
interface AcronymModel {
  /**
   * Returns whether the acronym model has an acronym for the token.
   *
   * @param token The token.
   * @return True if there are acronyms with the specified token text, False otherwise.
   */
  boolean hasAcronym(GenericLabel token);

  /**
   * Finds the best sense for a
   *
   * @param allTokens The list of tokens that make up the acronym.
   * @param forTokenIndex
   * @return
   */
  List<ScoredSense> findBestSense(List<? extends GenericLabel> allTokens, int forTokenIndex);

  /**
   * For deidentification: remove a single word from the model entirely
   *
   * @param word the word to remove
   */
  void removeWord(String word);

  /**
   * Remove all words except a determined set from the model
   *
   * @param words a set of the words to keep
   */
  void removeWordsExcept(Set<String> words);
}
