package edu.umn.biomedicus.rtf.reader;

import java.nio.ByteBuffer;

public class PlainTextSink implements RtfSink {
  private final StringBuilder builder = new StringBuilder();
  private boolean documentDestination = false;

  @Override
  public void handleBinary(ByteBuffer byteBuffer, int startIndex, int endIndex) {

  }

  @Override
  public void writeCharacter(String destinationName, char c, int startIndex, int endIndex) {
    if (destinationName.equals("Rtf")) {
      builder.append(c);
    }
  }

  @Override
  public void propertyChanged(String destinationName, String propertyGroup, String propertyName, int oldValue, int newValue) {

  }

  public String getText() {
    return builder.toString();
  }
}
