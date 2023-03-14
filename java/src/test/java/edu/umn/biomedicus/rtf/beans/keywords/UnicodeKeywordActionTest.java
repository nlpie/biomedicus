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

import java.io.IOException;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

class UnicodeKeywordActionTest {

  private RtfSink sink;
  private RtfState state;

  @BeforeEach
  void setUp() {
    sink = mock(RtfSink.class);
    Map<String, Map<String, Integer>> groupsMap = new HashMap<>();
    groupsMap.put("CharacterFormatting", new HashMap<>());
    groupsMap.put("DocumentFormatting", Collections.singletonMap("UnicodeByteCount", 1));
    state = new RtfState(groupsMap);
    state.setPropertyValue("CharacterFormatting", "Hidden", 0);
  }

  @Test
  void unicodeKeyword() throws IOException {
    UnicodeKeywordAction action = new UnicodeKeywordAction();
    action.setBegin(0);
    action.setEnd(6);
    action.setParameter(8226);
    RtfSource source = new RtfSource(null);
    action.executeAction(state, source, sink);
    verify(sink).writeCharacter(state.getDestination(), (char) 8226, 0, 6);
  }
}