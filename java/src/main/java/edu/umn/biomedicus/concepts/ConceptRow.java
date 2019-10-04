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

package edu.umn.biomedicus.concepts;

import java.nio.ByteBuffer;
import java.util.Objects;

public class ConceptRow {
  public static final int NUM_BYTES = 16;

  private final SUI sui;
  private final CUI cui;
  private final TUI tui;
  private final int source;

  public ConceptRow(SUI sui, CUI cui, TUI tui, int source) {
    this.sui = sui;
    this.cui = cui;
    this.tui = tui;
    this.source = source;
  }

  public SUI getSui() {
    return sui;
  }

  public CUI getCui() {
    return cui;
  }

  public TUI getTui() {
    return tui;
  }

  public int getSource() {
    return source;
  }

  public byte[] getBytes() {
    return ByteBuffer.allocate(16)
        .putInt(sui.identifier())
        .putInt(cui.identifier())
        .putInt(tui.identifier())
        .putInt(source)
        .array();
  }

  public static ConceptRow next(ByteBuffer buffer) {
    return new ConceptRow(
        new SUI(buffer.getInt()),
        new CUI(buffer.getInt()),
        new TUI(buffer.getInt()),
        buffer.getInt()
    );
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (o == null || getClass() != o.getClass()) return false;
    ConceptRow that = (ConceptRow) o;
    return source == that.source &&
        sui.equals(that.sui) &&
        cui.equals(that.cui) &&
        tui.equals(that.tui);
  }

  @Override
  public int hashCode() {
    return Objects.hash(sui, cui, tui, source);
  }

  @Override
  public String toString() {
    return "ConceptRow{" +
        "sui=" + sui +
        ", cui=" + cui +
        ", tui=" + tui +
        ", source=" + source +
        '}';
  }
}
