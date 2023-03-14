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

package edu.umn.biomedicus.rtf.beans.keywords;

import edu.umn.biomedicus.rtf.reader.RtfSink;
import edu.umn.biomedicus.rtf.reader.RtfSource;
import edu.umn.biomedicus.rtf.reader.RtfState;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.io.BufferedInputStream;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.HashMap;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class BinaryKeywordActionTest {

  private RtfState state;
  private RtfSink sink;

  @BeforeEach
  void setUp() {
    state = new RtfState(new HashMap<>());
    sink = mock(RtfSink.class);
  }

  @Test
  void readBytes() throws IOException {
    ByteBuffer input = ByteBuffer.allocate(9);
    input.put((byte) '\\');
    input.put((byte) 'b');
    input.put((byte) 'i');
    input.put((byte) 'n');
    input.put((byte) '3');
    input.put((byte) ' ');
    input.put((byte) 0xBA);
    input.put((byte) 0x1A);
    input.put((byte) 0x2A);
    BinaryKeywordAction keywordAction = new BinaryKeywordAction();
    keywordAction.setBegin(0);
    keywordAction.setEnd(6);
    keywordAction.setParameter(3);
    keywordAction.setControlWord("");
    RtfSource source = new RtfSource(new BufferedInputStream(new ByteArrayInputStream(input.array())));
    for (int i = 0; i < 6; i++) {
      source.read();
    }
    keywordAction.executeAction(state, source, sink);
    ArgumentCaptor<ByteBuffer> captor = ArgumentCaptor.forClass(ByteBuffer.class);
    verify(sink).handleBinary(captor.capture(), eq(0), eq(9));
    ByteBuffer bb = captor.getValue();
    assertEquals((byte) 0xBA, bb.get());
    assertEquals((byte) 0x1A, bb.get());
    assertEquals((byte) 0x2A, bb.get());
  }

  @Test
  void skipDestination() throws IOException {
    ByteBuffer input = ByteBuffer.allocate(9);
    input.put((byte) '\\');
    input.put((byte) 'b');
    input.put((byte) 'i');
    input.put((byte) 'n');
    input.put((byte) '3');
    input.put((byte) ' ');
    input.put((byte) 0xBA);
    input.put((byte) 0x1A);
    input.put((byte) 0x2A);
    BinaryKeywordAction keywordAction = new BinaryKeywordAction();
    keywordAction.setBegin(0);
    keywordAction.setEnd(6);
    keywordAction.setParameter(3);
    keywordAction.setControlWord("");
    RtfSource source = new RtfSource(new BufferedInputStream(new ByteArrayInputStream(input.array())));
    for (int i = 0; i < 6; i++) {
      source.read();
    }
    state.setSkippingDestination(true);
    keywordAction.executeAction(state, source, sink);
    verifyNoInteractions(sink);
  }
}
