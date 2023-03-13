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

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.*;

class PropertyKeywordActionTest {

  private RtfState state;
  private RtfSink sink;


  @BeforeEach
  void setUp() {
    HashMap<String, Integer> map = new HashMap<>();
    map.put("bar", 0);
    state = new RtfState(Collections.singletonMap("foo", map));
    state.setDestination("Rtf");
    sink = mock(RtfSink.class);
  }

  @Test
  void setProperty() throws IOException {
    PropertyKeywordAction action = new PropertyKeywordAction();
    action.setBegin(5);
    action.setEnd(10);
    action.setPropertyGroup("foo");
    action.setPropertyName("bar");
    action.setDefaultValue(1);
    action.setAlwaysUseDefault(false);
    action.setControlWord("foo");
    RtfSource source = new RtfSource(null);
    action.setParameter(4);
    action.executeAction(state, source, sink);
    verify(sink).propertyChanged("Rtf", "foo", "bar", 0, 4);
    assertEquals(4, state.getPropertyValue("foo", "bar"));
  }

  @Test
  void alwaysUseDefault() throws IOException {
    PropertyKeywordAction action = new PropertyKeywordAction();
    action.setBegin(5);
    action.setEnd(10);
    action.setPropertyGroup("foo");
    action.setPropertyName("bar");
    action.setDefaultValue(1);
    action.setAlwaysUseDefault(true);
    action.setControlWord("foo");
    RtfSource source = new RtfSource(null);
    action.setParameter(4);
    action.executeAction(state, source, sink);
    verify(sink).propertyChanged("Rtf", "foo", "bar", 0, 1);
    assertEquals(1, state.getPropertyValue("foo", "bar"));
  }

  @Test
  void skippingDestination() throws IOException {
    state.setSkippingDestination(true);
    PropertyKeywordAction action = new PropertyKeywordAction();
    action.setBegin(5);
    action.setEnd(10);
    action.setPropertyGroup("foo");
    action.setPropertyName("bar");
    action.setDefaultValue(1);
    action.setAlwaysUseDefault(false);
    action.setControlWord("foo");
    RtfSource source = new RtfSource(null);
    action.setParameter(4);
    action.executeAction(state, source, sink);
    verifyNoInteractions(sink);
    assertEquals(0, state.getPropertyValue("foo", "bar"));
  }

  @Test
  void usesDefault() throws IOException {
    PropertyKeywordAction action = new PropertyKeywordAction();
    action.setBegin(5);
    action.setEnd(10);
    action.setPropertyGroup("foo");
    action.setPropertyName("bar");
    action.setDefaultValue(1);
    action.setAlwaysUseDefault(false);
    action.setControlWord("foo");
    RtfSource source = new RtfSource(null);
    action.setParameter(null);
    action.executeAction(state, source, sink);
    verify(sink).propertyChanged("Rtf", "foo", "bar", 0, 1);
    assertEquals(1, state.getPropertyValue("foo", "bar"));
  }
}
