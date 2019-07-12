package edu.umn.biomedicus.rtf;

import edu.umn.biomedicus.rtf.reader.RtfParser;
import edu.umn.biomedicus.rtf.reader.RtfSource;
import edu.umn.nlpnewt.*;
import edu.umn.nlpnewt.common.JsonObject;
import edu.umn.nlpnewt.common.JsonObjectBuilder;
import edu.umn.nlpnewt.common.Server;
import edu.umn.nlpnewt.model.Event;
import edu.umn.nlpnewt.processing.EventProcessor;
import edu.umn.nlpnewt.processing.Processor;
import edu.umn.nlpnewt.processing.ProcessorServerBuilder;
import edu.umn.nlpnewt.processing.ProcessorServerOptions;
import org.jetbrains.annotations.NotNull;
import org.kohsuke.args4j.CmdLineException;
import org.kohsuke.args4j.CmdLineParser;

import java.io.BufferedInputStream;
import java.io.ByteArrayInputStream;
import java.io.IOException;

@Processor("biomedicus-rtf-processor")
public class RtfProcessor extends EventProcessor {

  private final RtfParser parser;

  public RtfProcessor() {
    parser = RTF.getParser();
  }

  public static void main(String[] args) {
    ProcessorServerOptions options = new ProcessorServerOptions();
    CmdLineParser cmdLineParser = new CmdLineParser(options);
    try {
      cmdLineParser.parseArgument(args);
      Server server = ProcessorServerBuilder.forProcessor(new RtfProcessor(), options).build();
      server.start();
      server.blockUntilShutdown();
    } catch (CmdLineException e) {
      // pass
    } catch (IOException | InterruptedException e) {
      e.printStackTrace();
    }
  }

  @Override
  public void process(@NotNull Event event, @NotNull JsonObject params, @NotNull JsonObjectBuilder result) {
    String binaryDataName = params.getStringValue("binary_data_name");
    if (binaryDataName == null) {
      binaryDataName = "rtf";
    }
    String outputDocumentName = params.getStringValue("output_document_name");
    if (outputDocumentName == null) {
      outputDocumentName = "plaintext";
    }
    try {
      byte[] bytes = event.getBinaryData().get(binaryDataName);
      ByteArrayInputStream bais = new ByteArrayInputStream(bytes);
      BufferedInputStream bis = new BufferedInputStream(bais);
      StringBuilder sb = new StringBuilder();
      bis.mark(6);
      for (int i = 0; i < 6; i++) {
        int code = bis.read();
        if (code != -1) {
          sb.append((char) code);
        }
      }
      if ("{\\rtf1".equals(sb.toString())) {
        bis.reset();
        RtfSource rtfSource = new RtfSource(bis);
        NewtDocumentRtfSink rtfSink = new NewtDocumentRtfSink();
        parser.parseRtf(rtfSource, rtfSink);
        rtfSink.done(event, outputDocumentName);
      } else {
        int code;
        while ((code = bis.read()) != -1) {
          sb.append((char) code);
        }
        event.addDocument(outputDocumentName, sb.toString());
      }
    } catch (IOException e) {
      throw new IllegalStateException(e);
    }
  }
}
