package edu.umn.biomedicus.rtf.beans.keywords;

import edu.umn.biomedicus.rtf.reader.KeywordAction;
import edu.umn.biomedicus.rtf.reader.RtfSink;
import edu.umn.biomedicus.rtf.reader.RtfSource;
import edu.umn.biomedicus.rtf.reader.RtfState;

import javax.xml.bind.annotation.XmlAttribute;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlRootElement;
import javax.xml.bind.annotation.XmlType;
import java.io.IOException;
import java.nio.charset.Charset;

@XmlRootElement
@XmlType
public class EncodingKeywordAction extends AbstractKeywordAction {

  private String encoding;

  @XmlElement(required = true)
  public String getEncoding() {
    return encoding;
  }

  public void setEncoding(String encoding) {
    this.encoding = encoding;
  }

  @Override
  public void executeAction(RtfState state, RtfSource source, RtfSink sink) throws IOException {
    state.setDecoder(Charset.forName(encoding).newDecoder());
  }

  @Override
  public KeywordAction copy() {
    EncodingKeywordAction action = new EncodingKeywordAction();
    action.setEncoding(encoding);
    return action;
  }
}
