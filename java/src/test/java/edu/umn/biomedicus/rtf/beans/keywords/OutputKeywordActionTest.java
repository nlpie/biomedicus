package edu.umn.biomedicus.rtf.beans.keywords;

import edu.umn.biomedicus.rtf.reader.RtfSink;
import edu.umn.biomedicus.rtf.reader.RtfState;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.util.Collections;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.*;

class OutputKeywordActionTest {
  private RtfState state;
  private RtfSink sink;

  @BeforeEach
  void setUp() {
    state = new RtfState(Collections.emptyMap());
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
    verifyZeroInteractions(sink);
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
    verifyZeroInteractions(sink);
  }

  @Test
  void hexKeywordAction() throws IOException {
    OutputKeywordAction action = new OutputKeywordAction();
    action.setControlWord("foo");
    action.setBegin(0);
    action.setEnd(2);
    action.setOutputString("z");
    action.executeAction(state, null, sink);
    verify(sink).writeCharacter(null, 'z', 0, 2);  // bullet point
  }
}
