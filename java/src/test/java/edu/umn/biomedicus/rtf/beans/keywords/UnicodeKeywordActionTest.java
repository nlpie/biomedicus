package edu.umn.biomedicus.rtf.beans.keywords;

import edu.umn.biomedicus.rtf.reader.RtfSink;
import edu.umn.biomedicus.rtf.reader.RtfSource;
import edu.umn.biomedicus.rtf.reader.RtfState;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

class UnicodeKeywordActionTest {

  private RtfSink sink;
  private RtfState state;

  @BeforeEach
  void setUp() {
    sink = mock(RtfSink.class);
    state = new RtfState(null);
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