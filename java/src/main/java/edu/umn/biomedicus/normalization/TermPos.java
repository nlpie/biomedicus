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

import edu.umn.biomedicus.common.pos.PartOfSpeech;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.Objects;

/**
 * A storage / hash map key object that is a tuple of a term and a part of speech.
 *
 * @author Ben Knoll
 * @since 1.7.0
 */
public final class TermPos implements Comparable<TermPos> {
  private final PartOfSpeech partOfSpeech;
  private final String term;

  public TermPos(String term, PartOfSpeech partOfSpeech) {
    this.term = Objects.requireNonNull(term, "Term must not be null");
    this.partOfSpeech = Objects.requireNonNull(partOfSpeech, "Part of speech must not be null.");
  }

  public TermPos(byte[] bytes) {
    ByteBuffer wrap = ByteBuffer.wrap(bytes);
    partOfSpeech = PartOfSpeech.values()[wrap.getInt()];
    term = StandardCharsets.UTF_8.decode(wrap).toString();
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) {
      return true;
    }
    if (o == null || getClass() != o.getClass()) {
      return false;
    }
    TermPos termPos = (TermPos) o;
    if (!term.equals(termPos.term)) {
      return false;
    }
    return partOfSpeech == termPos.partOfSpeech;
  }

  @Override
  public int hashCode() {
    int result = term.hashCode();
    result = 31 * result + partOfSpeech.hashCode();
    return result;
  }

  @Override
  public int compareTo(TermPos o) {
    int i = term.compareTo(o.term);
    if (i != 0) {
      return i;
    }
    return partOfSpeech.compareTo(o.partOfSpeech);
  }

  public byte[] getBytes() {
    byte[] bytes = term.getBytes();
    return ByteBuffer.allocate(Integer.BYTES + bytes.length).putInt(partOfSpeech.ordinal()).put(bytes).array();
  }
}
