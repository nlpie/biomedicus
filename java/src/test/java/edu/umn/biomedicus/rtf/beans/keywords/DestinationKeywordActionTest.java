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
    verifyZeroInteractions(sink);
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
