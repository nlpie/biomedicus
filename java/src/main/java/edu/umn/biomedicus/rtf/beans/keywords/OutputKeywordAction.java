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

package edu.umn.biomedicus.rtf.beans.keywords;

import edu.umn.biomedicus.rtf.reader.*;

import jakarta.xml.bind.annotation.XmlElement;
import jakarta.xml.bind.annotation.XmlRootElement;
import jakarta.xml.bind.annotation.XmlType;
import java.io.IOException;

/**
 *
 */
@XmlRootElement
@XmlType
public class OutputKeywordAction extends AbstractKeywordAction {

  private String outputString;

  @XmlElement(required = true)
  public String getOutputString() {
    return outputString;
  }

  public void setOutputString(String outputString) {
    this.outputString = outputString;
  }

  @Override
  public void executeAction(RtfState state, RtfSource source, RtfSink sink) throws IOException {
    if (state.isSkippingDestination()) {
      return;
    }
    int charactersToSkip = state.getCharactersToSkip();
    if (charactersToSkip > 0) {
      state.setCharactersToSkip(charactersToSkip - 1);
      return;
    }
    if (state.getPropertyValue("CharacterFormatting", "Hidden") > 0) {
      return;
    }
    for (char c : outputString.toCharArray()) {
      sink.writeCharacter(state.getDestination(), c, getStartIndex(), getEnd());
    }
  }

  @Override
  public KeywordAction copy() {
    OutputKeywordAction outputKeywordAction = new OutputKeywordAction();
    outputKeywordAction.setOutputString(outputString);
    return outputKeywordAction;
  }
}
