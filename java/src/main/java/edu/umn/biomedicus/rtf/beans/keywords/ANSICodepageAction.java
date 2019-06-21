package edu.umn.biomedicus.rtf.beans.keywords;

import edu.umn.biomedicus.rtf.reader.KeywordAction;
import edu.umn.biomedicus.rtf.reader.RtfSink;
import edu.umn.biomedicus.rtf.reader.RtfSource;
import edu.umn.biomedicus.rtf.reader.RtfState;

import javax.xml.bind.annotation.XmlRootElement;
import javax.xml.bind.annotation.XmlType;
import java.nio.charset.Charset;

@XmlRootElement
@XmlType
public class ANSICodepageAction extends AbstractKeywordAction {
  @Override
  public void executeAction(RtfState state, RtfSource source, RtfSink sink) {
    state.setDecoder(Charset.forName("cp" + getParameter()).newDecoder());
  }

  @Override
  public KeywordAction copy() {
    return new ANSICodepageAction();
  }
}
