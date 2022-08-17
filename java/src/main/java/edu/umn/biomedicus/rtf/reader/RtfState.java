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

package edu.umn.biomedicus.rtf.reader;

import java.nio.charset.Charset;
import java.nio.charset.CharsetDecoder;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Stores the stateful properties of rtf processing.
 */
public class RtfState {

  private final Map<String, Map<String, Integer>> properties;

  private CharsetDecoder decoder = Charset.forName("windows-1252").newDecoder();

  private int charactersToSkip = 0;

  private boolean skipDestinationIfUnknown = false;

  private boolean skippingDestination = false;

  private String destination = "Rtf";

  public RtfState(Map<String, Map<String, Integer>> properties) {
    this.properties = properties;
  }

  /**
   * Creates a child state object, which inherits the current values from this state object.
   *
   * @return new state object with the same values as this object.
   */
  public RtfState copy() {
    Map<String, Map<String, Integer>> propertiesCopy = properties.entrySet()
        .stream()
        .collect(Collectors.toMap(Map.Entry::getKey,
            entry -> entry.getValue()
                .entrySet()
                .stream()
                .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue))));

    RtfState copy = new RtfState(propertiesCopy);
    copy.charactersToSkip = charactersToSkip;
    copy.skipDestinationIfUnknown = skipDestinationIfUnknown;
    copy.skippingDestination = skippingDestination;
    copy.destination = destination;
    return copy;
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

  public Map<String, Integer> getPropertyGroup(String group) {
    return properties.get(group);
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

  public boolean isSkipDestinationIfUnknown() {
    return skipDestinationIfUnknown;
  }

  public void setSkipDestinationIfUnknown(boolean skipDestinationIfUnknown) {
    this.skipDestinationIfUnknown = skipDestinationIfUnknown;
  }

  public boolean isSkippingDestination() {
    return skippingDestination;
  }

  public void setSkippingDestination(boolean skippingDestination) {
    this.skippingDestination = skippingDestination;
  }

  public void setDestination(String destinationName) {
    destination = destinationName;
  }

  public String getDestination() {
    return destination;
  }
}
