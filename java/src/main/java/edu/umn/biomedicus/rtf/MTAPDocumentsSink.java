/*
 * Copyright 2019 Regents of the University of Minnesota.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package edu.umn.biomedicus.rtf;

import edu.umn.biomedicus.rtf.reader.RtfSink;
import edu.umn.nlpie.mtap.model.Document;
import edu.umn.nlpie.mtap.model.Event;
import edu.umn.nlpie.mtap.model.GenericLabel;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.List;

public class MTAPDocumentsSink implements RtfSink {

  private static final Logger LOGGER = LoggerFactory.getLogger(MTAPDocumentsSink.class);

  private final StringBuilder sb = new StringBuilder();

  private final List<PropertyWatcher> propertyWatchers = new ArrayList<>();
  public MTAPDocumentsSink() {
    propertyWatchers.add(
        new PropertyWatcher("bold", "CharacterFormatting", "Bold", 1, false, false)
    );
    propertyWatchers.add(
        new PropertyWatcher("italic", "CharacterFormatting", "Italic", 1, false, false)
    );
    propertyWatchers.add(
        new PropertyWatcher("underlined", "CharacterFormatting", "Underline", 1, false, false)
    );
  }

  public StringBuilder getSb() {
    return sb;
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
    if (destinationName == null) {
      LOGGER.error("Attempted to change property {}:{} from {} to {} with null destination at {}",
          propertyGroup, propertyName, oldValue, newValue, sb.length());
      LOGGER.error(sb.toString());
      throw new IllegalStateException();
    }
    if (destinationName.equals("Rtf")) {
      for (PropertyWatcher propertyWatcher : propertyWatchers) {
        propertyWatcher.propertyChanged(sb.length(), propertyGroup, propertyName, oldValue, newValue);
      }
    }
  }

  Document done(Event event, String documentName) {
    Document document = event.createDocument(documentName, sb.toString());
    for (PropertyWatcher propertyWatcher : propertyWatchers) {
      propertyWatcher.done(document);
    }
    return document;
  }

  @Override
  public void fatalError(Exception e) {
    LOGGER.error("Document at fatal error:");
    LOGGER.error(sb.toString());
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
            GenericLabel.Builder builder = GenericLabel.withSpan(startIndex, index);
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
