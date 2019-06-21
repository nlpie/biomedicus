package edu.umn.biomedicus.rtf.beans.keywords;

import edu.umn.biomedicus.rtf.reader.RtfSink;
import edu.umn.biomedicus.rtf.reader.RtfSource;
import edu.umn.biomedicus.rtf.reader.RtfState;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.BufferedInputStream;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.util.Collections;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.*;

class HexKeywordActionTest {
  private RtfState state;
  private RtfSink sink;

  @BeforeEach
  void setUp() {
    state = new RtfState(Collections.emptyMap());
    sink = mock(RtfSink.class);
  }

  @Test
  void charactersToSkip() throws IOException {
    byte[] bytes = "\\'95".getBytes();
    ByteArrayInputStream bais = new ByteArrayInputStream(bytes);
    RtfSource source = new RtfSource(new BufferedInputStream(bais));
    for (int i = 0; i < 2; i++) {
      source.read();
    }
    HexKeywordAction action = new HexKeywordAction();
    action.setControlWord("'");
    action.setBegin(0);
    action.setEnd(2);
    state.setCharactersToSkip(2);
    action.executeAction(state, source, sink);
    assertEquals(1, state.getCharactersToSkip());
    verifyNoMoreInteractions(sink);
  }

  @Test
  void skippingDestination() throws IOException {
    byte[] bytes = "\\'95".getBytes();
    ByteArrayInputStream bais = new ByteArrayInputStream(bytes);
    RtfSource source = new RtfSource(new BufferedInputStream(bais));
    for (int i = 0; i < 2; i++) {
      source.read();
    }
    HexKeywordAction action = new HexKeywordAction();
    action.setControlWord("'");
    action.setBegin(0);
    action.setEnd(2);
    state.setSkippingDestination(true);
    action.executeAction(state, source, sink);
    verifyNoMoreInteractions(sink);
  }

  @Test
  void hexKeywordAction() throws IOException {
    byte[] bytes = "\\'95".getBytes();
    ByteArrayInputStream bais = new ByteArrayInputStream(bytes);
    RtfSource source = new RtfSource(new BufferedInputStream(bais));
    for (int i = 0; i < 2; i++) {
      source.read();
    }
    HexKeywordAction action = new HexKeywordAction();
    action.setControlWord("'");
    action.setBegin(0);
    action.setEnd(2);
    action.executeAction(state, source, sink);
    verify(sink).writeCharacter(null, (char) 8226, 0, 4);  // bullet point
  }
}
