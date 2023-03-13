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

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verifyNoInteractions;

class SkipDestinationIfUnknownKeywordActionTest {

  private RtfSink sink;
  private RtfState state;

  @BeforeEach
  void setUp() {
    state = new RtfState(null);
    sink = mock(RtfSink.class);
  }

  @Test
  void setsSkipDestinationIfUnknown() {
    RtfSource source = new RtfSource(null);
    SkipDestinationIfUnknownKeywordAction action = new SkipDestinationIfUnknownKeywordAction();
    action.executeAction(state, source, sink);
    verifyNoInteractions(sink);
    assertTrue(state.isSkipDestinationIfUnknown());
  }
}