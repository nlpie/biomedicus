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

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.*;

class DestinationKeywordActionTest {

  private RtfState state;
  private RtfSink sink;

  @BeforeEach
  void setUp() {
    state = new RtfState(Collections.emptyMap());
    sink = mock(RtfSink.class);
  }

  @Test
  void skippingDestination() {
    state.setSkippingDestination(true);
    DestinationKeywordAction destinationKeywordAction = new DestinationKeywordAction();
    destinationKeywordAction.setControlWord("title");
    destinationKeywordAction.setDestinationName("Title");
    destinationKeywordAction.setBegin(45);
    destinationKeywordAction.setEnd(50);
    destinationKeywordAction.executeAction(state, null, sink);
    verifyNoInteractions(sink);
  }

  @Test
  void changeDestination() {
    DestinationKeywordAction destinationKeywordAction = new DestinationKeywordAction();
    destinationKeywordAction.setControlWord("title");
    destinationKeywordAction.setDestinationName("Title");
    destinationKeywordAction.setBegin(45);
    destinationKeywordAction.setEnd(50);
    destinationKeywordAction.executeAction(state, null, sink);
    assertEquals("Title", state.getDestination());
  }
}
