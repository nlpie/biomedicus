package edu.umn.biomedicus.rtf;

import edu.umn.biomedicus.rtf.reader.RtfParser;
import edu.umn.biomedicus.rtf.reader.RtfSource;
import edu.umn.nlpnewt.*;
import org.jetbrains.annotations.NotNull;
import org.kohsuke.args4j.CmdLineException;

import java.io.BufferedInputStream;
import java.io.ByteArrayInputStream;
import java.io.IOException;

@Processor("biomedicus-rtf-processor")
public class RtfProcessor extends EventProcessor {

  private final RtfParser parser;

  public RtfProcessor() {
    parser = RTF.getParser();
  }

  @Override
  public void process(@NotNull Event event, @NotNull JsonObject params, @NotNull JsonObjectBuilder result) {
    String binaryDataName = params.getStringValue("binary_data_name");
    if (binaryDataName == null) {
      binaryDataName = "rtf";
    }
    String outputDocumentName = params.getStringValue("output_document_name");
    byte[] bytes = event.getBinaryData().get(binaryDataName);
    ByteArrayInputStream bais = new ByteArrayInputStream(bytes);
    BufferedInputStream bis = new BufferedInputStream(bais);
    RtfSource rtfSource = new RtfSource(bis);
    NewtDocumentRtfSink rtfSink = new NewtDocumentRtfSink();
    try {
      parser.parseRtf(rtfSource, rtfSink);
    } catch (IOException e) {
      throw new IllegalStateException(e);
    }
    rtfSink.done(event, outputDocumentName);
  }

  public static void main(String[] args) {
    try {
      ProcessorServerOptions options = ProcessorServerOptions.parseArgs(args);
      options.setProcessor(new RtfProcessor());
      Newt newt = new Newt();
      Server server = newt.createProcessorServer(options);
      server.start();
      server.blockUntilShutdown();
    } catch (CmdLineException e) {
      // pass
    } catch (IOException | InterruptedException e) {
      e.printStackTrace();
    }
  }
}
