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

import edu.umn.biomedicus.rtf.beans.keywords.ControlKeywordsDescription;
import edu.umn.biomedicus.rtf.beans.properties.PropertiesDescription;
import edu.umn.biomedicus.rtf.reader.KeywordAction;
import edu.umn.biomedicus.rtf.reader.RtfParser;
import edu.umn.biomedicus.rtf.reader.RtfParserFactory;
import edu.umn.biomedicus.rtf.reader.RtfState;

import java.io.IOException;
import java.util.Map;

public class RTF {
  public static RtfParser getParser() throws IOException {
    ControlKeywordsDescription controlKeywordsDescription = ControlKeywordsDescription
        .loadFromFile("edu/umn/biomedicus/rtf/ControlKeywords.xml");
    Map<String, KeywordAction> keywordActionMap = controlKeywordsDescription
        .getKeywordActionsAsMap();
    PropertiesDescription propertiesDescription = PropertiesDescription
        .loadFromFile("edu/umn/biomedicus/rtf/PropertiesDescription.xml");
    Map<String, Map<String, Integer>> properties = propertiesDescription.createProperties();
    RtfState state = new RtfState(properties);
    return new RtfParser(keywordActionMap, state);
  }

  public static RtfParserFactory getFactory() throws IOException {
    ControlKeywordsDescription controlKeywordsDescription = ControlKeywordsDescription
        .loadFromFile("edu/umn/biomedicus/rtf/ControlKeywords.xml");
    Map<String, KeywordAction> keywordActionMap = controlKeywordsDescription
        .getKeywordActionsAsMap();
    PropertiesDescription propertiesDescription = PropertiesDescription
        .loadFromFile("edu/umn/biomedicus/rtf/PropertiesDescription.xml");
    return new RtfParserFactory(keywordActionMap, propertiesDescription);
  }
}
