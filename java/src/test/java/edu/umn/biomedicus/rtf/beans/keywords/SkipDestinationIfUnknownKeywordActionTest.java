package edu.umn.biomedicus.rtf.beans.keywords;

import edu.umn.biomedicus.rtf.reader.RtfSink;
import edu.umn.biomedicus.rtf.reader.RtfSource;
import edu.umn.biomedicus.rtf.reader.RtfState;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verifyZeroInteractions;

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
    verifyZeroInteractions(sink);
    assertTrue(state.isSkipDestinationIfUnknown());
  }
}