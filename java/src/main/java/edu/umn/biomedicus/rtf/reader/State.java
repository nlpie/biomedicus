/*
 * Copyright 2019 Regents of the University of Minnesota
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

package edu.umn.biomedicus.rtf.reader;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.charset.Charset;
import java.nio.charset.CharsetDecoder;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Stores the stateful properties of rtf processing.
 */
public class State {

  private static final Logger LOGGER = LoggerFactory.getLogger(State.class);

  /**
   * Various properties changed by property value keywords.
   */
  private final Map<String, Map<String, Integer>> properties;

  private CharsetDecoder decoder = Charset.forName("Windows-1252").newDecoder();

  private int charactersToSkip = 0;

  public State(Map<String, Map<String, Integer>> properties) {
    this.properties = properties;
  }

  /**
   * Copies a child state object, which inherits the current values from this state object.
   *
   * @return new state object with the same values as this object.
   */
  public State copy() {
    Map<String, Map<String, Integer>> propertiesCopy = properties.entrySet()
        .stream()
        .collect(Collectors.toMap(Map.Entry::getKey,
            entry -> entry.getValue()
                .entrySet()
                .stream()
                .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue))));

    return new State(propertiesCopy);
  }

  /**
   * Sets a property value in the state.
   *
   * @param group    the property group name.
   * @param property the property name.
   * @param value    the value to set the property to.
   */
  public void setPropertyValue(String group, String property, int value) {
    properties.get(group).put(property, value);
  }

  /**
   * Resets a property group to zeroes.
   *
   * @param group the property group.
   */
  public void resetPropertyGroup(String group) {
    properties.get(group).replaceAll((k, v) -> 0);
  }

  /**
   * Returns the value of a property.
   *
   * @param group    the group name of the property.
   * @param property the property name.
   *
   * @return the value of the property.
   */
  public int getPropertyValue(String group, String property) {
    Map<String, Integer> propertyGroup = properties.get(group);
    if (propertyGroup == null) {
      throw new IllegalArgumentException("Group not found");
    }
    Integer propertyValue = propertyGroup.get(property);
    if (propertyValue == null) {
      throw new IllegalArgumentException("Property not found");
    }
    return propertyValue;
  }

  public CharsetDecoder getDecoder() {
    return decoder;
  }

  public void setDecoder(CharsetDecoder decoder) {
    this.decoder = decoder;
  }

  public int getCharactersToSkip() {
    return charactersToSkip;
  }

  public void setCharactersToSkip(int charactersToSkip) {
    this.charactersToSkip = charactersToSkip;
  }

  public int getAndDecrementCharactersToSkip() {
    return charactersToSkip--;
  }
}
