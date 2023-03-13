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

import edu.umn.biomedicus.rtf.reader.KeywordAction;

import jakarta.xml.bind.JAXB;
import jakarta.xml.bind.annotation.XmlElement;
import jakarta.xml.bind.annotation.XmlElementWrapper;
import jakarta.xml.bind.annotation.XmlRootElement;
import jakarta.xml.bind.annotation.XmlType;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 *
 */
@XmlRootElement
@XmlType
public class ControlKeywordsDescription {

  private List<ControlKeyword> controlKeywords;

  public static ControlKeywordsDescription loadFromFile(String classpath) throws IOException {
    try (
        InputStream inputStream = Thread.currentThread()
            .getContextClassLoader()
            .getResourceAsStream(classpath)
    ) {
      if (inputStream == null) {
        throw new FileNotFoundException();
      }
      return JAXB.unmarshal(inputStream, ControlKeywordsDescription.class);
    }
  }

  @XmlElementWrapper(required = true)
  @XmlElement(name = "controlKeyword")
  public List<ControlKeyword> getControlKeywords() {
    return controlKeywords;
  }

  public void setControlKeywords(List<ControlKeyword> controlKeywords) {
    this.controlKeywords = controlKeywords;
  }

  public Map<String, KeywordAction> getKeywordActionsAsMap() {
    return controlKeywords.stream()
        .collect(Collectors.toMap(ControlKeyword::getKeyword, ControlKeyword::getKeywordAction));
  }
}
