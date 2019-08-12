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

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

class PropertyResetKeywordActionTest {

  private RtfState state;
  private RtfSink sink;

  @BeforeEach
  void setUp() {
    HashMap<String, Integer> map = new HashMap<>();
    map.put("bar", 1);
    map.put("baz", 2);
    state = new RtfState(Collections.singletonMap("foo", map));
    sink = mock(RtfSink.class);
  }

  @Test
  void resets() throws IOException {
    state.setDestination("Rtf");
    PropertyResetKeywordAction action = new PropertyResetKeywordAction();
    action.setBegin(5);
    action.setEnd(10);
    action.setPropertyGroupName("foo");
    RtfSource source = new RtfSource(null);
    action.executeAction(state, source, sink);
    verify(sink).propertyChanged("Rtf", "foo", "bar", 1, 0);
    verify(sink).propertyChanged("Rtf", "foo", "baz", 2, 0);
    assertEquals(0, state.getPropertyValue("foo", "bar"));
    assertEquals(0, state.getPropertyValue("foo", "baz"));
  }
}
