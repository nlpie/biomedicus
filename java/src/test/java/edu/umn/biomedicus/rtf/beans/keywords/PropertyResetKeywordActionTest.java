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
    PropertyResetKeywordAction action = new PropertyResetKeywordAction();
    action.setBegin(5);
    action.setEnd(10);
    action.setPropertyGroupName("foo");
    RtfSource source = new RtfSource(null);
    action.executeAction(state, source, sink);
    verify(sink).propertyChanged(, "foo", "bar", 1, 0);
    verify(sink).propertyChanged(, "foo", "baz", 2, 0);
    assertEquals(0, state.getPropertyValue("foo", "bar"));
    assertEquals(0, state.getPropertyValue("foo", "baz"));
  }
}
