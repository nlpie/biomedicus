package edu.umn.biomedicus.rtf;

import edu.umn.biomedicus.rtf.reader.RtfSink;
import edu.umn.nlpnewt.model.Document;
import edu.umn.nlpnewt.model.Event;
import edu.umn.nlpnewt.model.GenericLabel;
import edu.umn.nlpnewt.model.Labeler;

import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.List;

public class NewtDocumentRtfSink implements RtfSink {

  private final StringBuilder sb = new StringBuilder();
  private final List<PropertyWatcher> propertyWatchers = new ArrayList<>();

  public NewtDocumentRtfSink() {
    propertyWatchers.add(
        new PropertyWatcher("biomedicus.bold", "CharacterFormatting", "Bold", 1, false, false)
    );
    propertyWatchers.add(
        new PropertyWatcher("biomedicus.italic", "CharacterFormatting", "Italic", 1, false, false)
    );
    propertyWatchers.add(
        new PropertyWatcher("biomedicus.underline", "CharacterFormatting", "Underline", 1, false, false)
    );
  }

  @Override
  public void handleBinary(ByteBuffer byteBuffer, int startIndex, int endIndex) {

  }

  @Override
  public void writeCharacter(String destinationName, char c, int startIndex, int endIndex) {
    if (destinationName.equals("Rtf")) {
      sb.append(c);
    }
  }

  @Override
  public void propertyChanged(String destinationName,
                              String propertyGroup,
                              String propertyName,
                              int oldValue,
                              int newValue) {
    if (destinationName.equals("Rtf")) {
      for (PropertyWatcher propertyWatcher : propertyWatchers) {
        propertyWatcher.propertyChanged(sb.length(), propertyGroup, propertyName, oldValue, newValue);
      }
    }
  }

  Document done(Event event, String documentName) {
    Document document = event.addDocument(documentName, sb.toString());
    for (PropertyWatcher propertyWatcher : propertyWatchers) {
      propertyWatcher.done(document);
    }
    return document;
  }

  private static class PropertyWatcher {
    private final String labelIndex;
    private final String propertyGroup;
    private final String propertyName;
    private final int minimumValue;
    private final boolean valueIncluded;
    private final boolean zeroLengthEmitted;
    private final List<GenericLabel> labels = new ArrayList<>();
    private int startIndex = -1;

    public PropertyWatcher(String labelIndex,
                           String propertyGroup,
                           String propertyName,
                           int minimumValue,
                           boolean valueIncluded,
                           boolean zeroLengthEmitted) {
      this.labelIndex = labelIndex;
      this.propertyGroup = propertyGroup;
      this.propertyName = propertyName;
      this.minimumValue = minimumValue;
      this.valueIncluded = valueIncluded;
      this.zeroLengthEmitted = zeroLengthEmitted;
    }

    void propertyChanged(int index,
                         String propertyGroup,
                         String propertyName,
                         int oldValue,
                         int newValue) {
      if (!this.propertyGroup.equals(propertyGroup) || !this.propertyName.equals(propertyName)) {
        return;
      }

      if (startIndex != -1) {
        if (newValue < minimumValue) {
          if (index != startIndex || zeroLengthEmitted) {
            GenericLabel.Builder builder = GenericLabel.newBuilder(startIndex, index);
            if (valueIncluded) {
              builder.setProperty("value", oldValue);
            }
            labels.add(builder.build());
          }
          startIndex = -1;
        }
      } else {
        if (newValue >= minimumValue) {
          startIndex = index;
        }
      }
    }

    void done(Document document) {
      if (labels.size() > 0) {
        document.addLabels(labelIndex, false, labels);
      }
    }
  }
}
