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
import edu.umn.biomedicus.rtf.reader.RtfState;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.util.Collections;
import java.util.HashMap;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.*;

class OutputKeywordActionTest {
  private RtfState state;
  private RtfSink sink;

  @BeforeEach
  void setUp() {
    state = new RtfState(Collections.singletonMap("CharacterFormatting", new HashMap<>()));
    state.setPropertyValue("CharacterFormatting", "Hidden", 0);
    sink = mock(RtfSink.class);
  }

  @Test
  void skippingDestination() throws IOException {
    OutputKeywordAction action = new OutputKeywordAction();
    action.setControlWord("foo");
    action.setBegin(0);
    action.setEnd(2);
    action.setOutputString("z");
    state.setSkippingDestination(true);
    action.executeAction(state, null, sink);
    verifyNoInteractions(sink);
  }

  @Test
  void charactersToSkip() throws IOException {
    OutputKeywordAction action = new OutputKeywordAction();
    action.setControlWord("foo");
    action.setBegin(0);
    action.setEnd(2);
    action.setOutputString("z");
    state.setCharactersToSkip(2);
    action.executeAction(state, null, sink);
    assertEquals(1, state.getCharactersToSkip());
    verifyNoInteractions(sink);
  }

  @Test
  void hexKeywordAction() throws IOException {
    OutputKeywordAction action = new OutputKeywordAction();
    action.setControlWord("foo");
    action.setBegin(0);
    action.setEnd(2);
    action.setOutputString("z");
    action.executeAction(state, null, sink);
    verify(sink).writeCharacter("Rtf", 'z', 0, 2);  // bullet point
  }
}
