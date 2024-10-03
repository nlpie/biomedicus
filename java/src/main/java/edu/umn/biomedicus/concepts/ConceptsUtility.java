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

package edu.umn.biomedicus.concepts;

import org.jetbrains.annotations.Nullable;
import org.kohsuke.args4j.CmdLineException;
import org.kohsuke.args4j.CmdLineParser;
import org.kohsuke.args4j.Option;
import org.rocksdb.RocksDBException;

import java.io.IOException;
import java.nio.file.Path;
import java.util.Scanner;

import static edu.umn.biomedicus.concepts.CUI.CUI_PATTERN;

/**
 * Utility
 */
public class ConceptsUtility {
  @Option(name = "--db-path", metaVar = "PATH_TO", usage = "Optional override path to the concepts dictionary.")
  private @Nullable Path dbPath = null;

  public void listenToConsole() throws IOException, RocksDBException {
    try (Scanner scanner = new Scanner(System.in)) {
      System.out.println("Reading concepts from database");

      DictionaryConceptDetector.ConceptsOptions conceptsOptions = new DictionaryConceptDetector.ConceptsOptions();
      conceptsOptions.setDbPath(dbPath);
      conceptsOptions.setInMemory(true);
      ConceptDictionary dictionary = DictionaryConceptDetector.loadConceptsDictionary(conceptsOptions);

      while (true) {
        System.out.print("Q: ");
        String query = scanner.nextLine();
        if ("!q".equals(query)) {
          return;
        } else if (CUI_PATTERN.matcher(query).matches()) {
          for (PhraseConcept phraseConcept : dictionary.withCui(new CUI(query))) {
            System.out.println(phraseConcept.toString());
          }
        } else {
          System.out.println("Searching for " + query);
          for (PhraseConcept phraseConcept : dictionary.withWord(query)) {
            System.out.println(phraseConcept.toString());
          }
        }
      }
    }
  }

  public static void main(String[] args) {
    ConceptsUtility conceptsUtility = new ConceptsUtility();
    CmdLineParser parser = new CmdLineParser(conceptsUtility);
    try {
      parser.parseArgument(args);
      conceptsUtility.listenToConsole();
    } catch (CmdLineException e) {
      System.err.println(e.getLocalizedMessage());
      parser.printUsage(System.err);
    } catch (RocksDBException | IOException e) {
      e.printStackTrace();
    }
  }
}
