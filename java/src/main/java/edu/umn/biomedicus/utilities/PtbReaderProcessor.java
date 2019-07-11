package edu.umn.biomedicus.utilities;

import edu.umn.biomedicus.common.pos.PartOfSpeech;
import edu.umn.biomedicus.common.pos.PartsOfSpeech;
import edu.umn.biomedicus.utilities.PtbReader.Node;
import edu.umn.nlpnewt.*;
import edu.umn.nlpnewt.common.JsonObject;
import edu.umn.nlpnewt.common.JsonObjectBuilder;
import edu.umn.nlpnewt.model.Document;
import edu.umn.nlpnewt.model.Event;
import edu.umn.nlpnewt.model.GenericLabel;
import edu.umn.nlpnewt.model.Labeler;
import edu.umn.nlpnewt.processing.*;
import org.jetbrains.annotations.NotNull;
import org.kohsuke.args4j.CmdLineException;
import org.kohsuke.args4j.CmdLineParser;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

@Processor("ptb-reader")
public class PtbReaderProcessor extends EventProcessor {
  @Override
  public void process(@NotNull Event event,
                      @NotNull JsonObject params,
                      @NotNull JsonObjectBuilder result) {
    String sourceDocumentName = params.getStringValue("source_document_name");
    if (sourceDocumentName == null) {
      sourceDocumentName = "ptb";
    }
    String targetDocumentName = params.getStringValue("target_document_name");
    if (targetDocumentName == null) {
      targetDocumentName = "plaintext";
    }

    List<GenericLabel> sentences = new ArrayList<>();
    List<GenericLabel> posTags = new ArrayList<>();
    StringBuilder documentBuilder = new StringBuilder();
    PtbReader reader = PtbReader.create(event.getDocuments().get(sourceDocumentName).getText());
    try {
      Node node;
      while ((node = reader.nextNode()) != null) {
        int sentBegin = documentBuilder.length();
        Iterator<Node> leafIterator = node.leafIterator();
        while (leafIterator.hasNext()) {
          Node leaf = leafIterator.next();
          if ("-NONE-".equals(leaf.getLabel())) {
            continue;
          }

          String word = leaf.getWord();
          if (word == null) {
            continue;
          }

          int begin = documentBuilder.length();
          int end = begin + word.length();
          documentBuilder.append(word).append(' ');
          String label = leaf.getLabel();
          PartOfSpeech partOfSpeech = PartsOfSpeech.forTagWithFallback(label);
          if (partOfSpeech == null) {
            partOfSpeech = PartOfSpeech.XX;
          }
          posTags.add(GenericLabel.newBuilder(begin, end)
              .setProperty("tag", partOfSpeech.toString())
              .build());

        }
        int sentEnd = documentBuilder.length();
        sentences.add(GenericLabel.newBuilder(sentBegin, sentEnd).build());
      }
    } catch (IOException e) {
      throw new IllegalStateException(e);
    }

    Document target = event.addDocument(targetDocumentName, documentBuilder.toString());
    target.addLabels("sentences", true, sentences);
    target.addLabels("pos_tags", true, posTags);
  }

  public static void main(String[] args) {
    ProcessorServerOptions options = new ProcessorServerOptions();
    CmdLineParser parser = new CmdLineParser(options);
    try {
      parser.parseArgument(args);
      ProcessorServer server = ProcessorServerBuilder
          .forProcessor(new PtbReaderProcessor(), options)
          .build();
      server.start();
      server.blockUntilShutdown();
    } catch (CmdLineException e) {
      ProcessorServerOptions.printHelp(parser, PtbReaderProcessor.class, e, null);
    } catch (InterruptedException | IOException e) {
      e.printStackTrace();
    }
  }
}
