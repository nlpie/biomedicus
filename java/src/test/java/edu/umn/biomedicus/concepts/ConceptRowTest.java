/*
 * Copyright 2020 Regents of the University of Minnesota.
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

import org.junit.jupiter.api.Test;

import java.nio.ByteBuffer;

import static org.junit.jupiter.api.Assertions.assertEquals;

public class ConceptRowTest {
  @Test
  void testToAndFromBytesCodeLessThan12() {
    ConceptRow conceptRow = new ConceptRow(new SUI(1234567), new CUI(1234567),
        new TUI(123), 1, "12345678");
    byte[] bytes = conceptRow.getBytes();
    ByteBuffer wrap = ByteBuffer.wrap(bytes);
    ConceptRow copy = ConceptRow.next(wrap);
    assertEquals(conceptRow, copy);
  }

  @Test
  void testToAndFromBytesCodeEquals12() {
    ConceptRow conceptRow = new ConceptRow(new SUI(1234567), new CUI(1234567),
        new TUI(123), 1, "123456789012");
    byte[] bytes = conceptRow.getBytes();
    ByteBuffer wrap = ByteBuffer.wrap(bytes);
    ConceptRow copy = ConceptRow.next(wrap);
    assertEquals(conceptRow, copy);
  }

  @Test
  void testToAndFromBytesCodeGreater12() {
    ConceptRow conceptRow = new ConceptRow(new SUI(1234567), new CUI(1234567),
        new TUI(123), 1, "1234567890123");
    byte[] bytes = conceptRow.getBytes();
    ByteBuffer wrap = ByteBuffer.wrap(bytes);
    ConceptRow copy = ConceptRow.next(wrap);
    assertEquals(conceptRow, copy);
  }
}
