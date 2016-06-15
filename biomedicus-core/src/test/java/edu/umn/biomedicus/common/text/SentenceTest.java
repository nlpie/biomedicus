/*
 * Copyright (c) 2016 Regents of the University of Minnesota.
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

package edu.umn.biomedicus.common.text;

import edu.umn.biomedicus.common.semantics.SubstanceUsageType;
import mockit.MockUp;
import org.testng.annotations.Test;

import java.util.Arrays;
import java.util.Collection;
import java.util.List;
import java.util.stream.Stream;

import static org.testng.Assert.assertEquals;

/**
 *
 */
public class SentenceTest {

    private Token first = new MockToken().getMockInstance();
    private Token second = new MockToken().getMockInstance();

    private Term firstTerm = new MockTerm().getMockInstance();
    private Term secondTerm = new MockTerm().getMockInstance();

    class MockToken extends MockUp<Token> {

    }

    class MockTerm extends MockUp<Term> {

    }

    class TestSentence implements Sentence {
        @Override
        public Stream<Token> tokens() {
            return Stream.of(first, second);
        }

        @Override
        public Stream<Term> terms() {
            return Stream.of(firstTerm, secondTerm);
        }

        @Override
        public String getDependencies() {
            return null;
        }

        @Override
        public void setDependencies(String dependencies) {

        }

        @Override
        public String getParseTree() {
            return null;
        }

        @Override
        public void setParseTree(String parseTree) {

        }

        @Override
        public boolean isSocialHistoryCandidate() {
            return false;
        }

        @Override
        public void setIsSocialHistoryCandidate(boolean isSocialHistoryCandidate) {

        }

        @Override
        public Collection<SubstanceUsageType> getSubstanceUsageTypes() {
            return null;
        }

        @Override
        public void addSubstanceUsageType(SubstanceUsageType substanceUsageType) {

        }

        @Override
        public String getText() {
            return null;
        }

        @Override
        public int getBegin() {
            return 0;
        }

        @Override
        public int getEnd() {
            return 0;
        }
    }

    Sentence sentence = new TestSentence();

    @Test
    public void testGetTokens() throws Exception {
        List<Token> tokens = sentence.getTokens();
        assertEquals(tokens, Arrays.asList(first, second), "Tokens should be list of two tokens");
    }

    @Test
    public void testGetTerms() throws Exception {
        List<Term> terms = sentence.getTerms();
        assertEquals(terms, Arrays.asList(firstTerm, secondTerm), "Terms should be list of two terms");
    }
}