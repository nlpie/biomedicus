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

package edu.umn.biomedicus.common.config;

import org.apache.commons.text.StringSubstitutor;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.yaml.snakeyaml.Yaml;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class Config {
  private static final StringSubstitutor SUBSTITUTOR = createSubstitutor();

  private static final StringSubstitutor createSubstitutor() {
    Map<String, String> env = new HashMap<>(System.getenv());
    if (!env.containsKey("BIOMEDICUS_DATA")) {
      env.put("BIOMEDICUS_DATA", Paths.get(System.getProperty("user.home")).resolve(".biomedicus").resolve("data").toString());
    }
    return new StringSubstitutor(env);
  }

  private static final Logger LOGGER = LoggerFactory.getLogger(Config.class);

  private final Map<String, Object> config;

  private Config(Map<String, Object> config) {
    this.config = config;
  }

  private Config(Config config) {
    this.config = new HashMap<>(config.config);
  }

  public static Config createByCopying(Config config) {
    Config newConfig = new Config(new HashMap<>());
    newConfig.update(config);
    return newConfig;
  }

  /**
   * Loads a configuration from one of the default locations if there is a configuration file
   * present.
   *
   * @return Configuration object containing the flattened key-values from the yaml file.
   */
  public static @NotNull Config loadFromDefaultLocations() {
    return loadConfigFromLocationOrDefaults(null);
  }

  /**
   * Loads a configuration from the parameter or one of the default locations if there is a
   * configuration file present. Will use the default config if none are present.
   *
   * @param configPath An optional path to a file to attempt to load configuration from.
   *
   * @return Configuration object containing the flattened key-values from the yaml file.
   */
  public static @NotNull Config loadConfigFromLocationOrDefaults(@Nullable Path configPath) {
    String envVarPath = System.getenv("BIOMEDICUS-CONFIG");
    List<Path> searchPaths = Arrays.asList(
        Paths.get("./biomedicusConfig.yml"),
        Paths.get(System.getProperty("user.home")).resolve(".biomedicus/biomedicusConfig.yml"),
        Paths.get("/etc/biomedicus/biomedicusConfig.yml"));
    if (envVarPath != null) {
      searchPaths.add(0, Paths.get(envVarPath));
    }
    if (configPath != null) {
      searchPaths.add(0, configPath);
    }
    for (Path path : searchPaths) {
      if (Files.exists(path)) {
        LOGGER.info("Using configuration file: {}", path);
        return loadConfig(path);
      }
    }
    return defaultConfig();
  }

  /**
   * Loads a configuration from the specified configPath.
   *
   * @param configFile Path to a configuration yaml file.
   *
   * @return Configuration object containing the flattened key-values from the yaml file.
   */
  public static @NotNull Config loadConfig(Path configFile) {
    try (InputStream inputStream = Files.newInputStream(configFile)) {
      LOGGER.info("Using default configuration.");
      return loadConfig(inputStream);
    } catch (IOException e) {
      throw new IllegalStateException("Failed to load configuration.", e);
    }
  }

  /**
   * The default configuration for nlp-newt.
   *
   * @return Configuration object containing default configuration.
   */
  public static @NotNull Config defaultConfig() {
    try (
        InputStream inputStream = Thread.currentThread().getContextClassLoader()
            .getResourceAsStream("edu/umn/biomedicus/defaultConfig.yml")
    ) {
      return loadConfig(inputStream);
    } catch (IOException e) {
      throw new IllegalStateException("Failed to load default configuration from classpath.");
    }
  }

  private static Config loadConfig(InputStream inputStream) {
    Yaml yaml = new Yaml();
    Map<String, Object> yamlMap = yaml.load(inputStream);
    Map<String, Object> config = new HashMap<>();
    flattenConfig(yamlMap, "", config);
    return new Config(config);
  }

  /**
   * A configuration containing no keys.
   *
   * @return Empty configuration object.
   */
  public static @NotNull Config emptyConfig() {
    return new Config(new HashMap<>());
  }

  @SuppressWarnings("unchecked")
  private static void flattenConfig(Map<String, Object> map,
                                    String prefix,
                                    Map<String, Object> targetMap) {
    for (Map.Entry<String, Object> entry : map.entrySet()) {
      String key = entry.getKey();
      Object value = entry.getValue();
      String newPrefix = prefix + (prefix.length() > 0 ? "." : "") + key;
      if (value instanceof Map) {
        flattenConfig((Map<String, Object>) value, newPrefix, targetMap);
      } else {
        if (value instanceof String) {
          value = SUBSTITUTOR.replace(value);
        }
        targetMap.put(newPrefix, value);
      }
    }
  }

  public Config copy() {
    return new Config(this);
  }

  public Object get(@NotNull String key) {
    return config.get(key);
  }

  public String getStringValue(@NotNull String key) {
    return (String) config.get(key);
  }

  public Integer getIntegerValue(@NotNull String key) {
    return (Integer) config.get(key);
  }

  public Double getDoubleValue(@NotNull String key) {
    return (Double) config.get(key);
  }

  public Boolean getBooleanValue(@NotNull String key) {
    return (Boolean) config.get(key);
  }

  public void update(Map<@NotNull String, @Nullable Object> updates) {
    config.putAll(updates);
  }

  public void update(Config config) {
    this.config.putAll(config.asMap());
  }


  public void set(@NotNull String key, @Nullable Object value) {
    config.put(key, value);
  }


  public Map<@NotNull String, @Nullable Object> asMap() {
    return config;
  }
}
