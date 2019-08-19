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

package edu.umn.biomedicus.normalization;

import org.jetbrains.annotations.Nullable;

import java.util.Map;

/**
 * Provides a hash map backed normalizer model.
 *
 * @author Ben Knoll
 * @since 1.8.0
 */
final class HashNormalizerModel implements NormalizerModel {

  private final Map<TermPos, String> normalizationMap;

  HashNormalizerModel(Map<TermPos, String> normalizationMap) {
    this.normalizationMap = normalizationMap;
  }

  @Override
  @Nullable
  public String get(TermPos termPos) {
    return normalizationMap.get(termPos);
  }

  @Override
  public void close() {}
}
