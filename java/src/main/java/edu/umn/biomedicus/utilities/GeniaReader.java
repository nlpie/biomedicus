package edu.umn.biomedicus.utilities;

import edu.umn.nlpnewt.common.JsonObject;
import edu.umn.nlpnewt.common.JsonObjectBuilder;
import edu.umn.nlpnewt.model.Event;
import edu.umn.nlpnewt.processing.EventProcessor;
import edu.umn.nlpnewt.processing.Processor;
import org.jetbrains.annotations.NotNull;

/**
 * Reader for the GENIA PTB XML corpus.
 */
@Processor("genia-ptb-reader")
public class GeniaReader extends EventProcessor {
  @Override
  public void process(@NotNull Event event, @NotNull JsonObject params, @NotNull JsonObjectBuilder result) {

  }
}
