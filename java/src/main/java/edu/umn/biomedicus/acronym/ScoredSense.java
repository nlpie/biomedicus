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

package edu.umn.biomedicus.acronym;

import org.jetbrains.annotations.NotNull;

import java.util.Objects;

/**
 * An acronym sense with its score.
 */
public class ScoredSense {
    private final String sense;
    private final double score;

    public ScoredSense(@NotNull String sense, double score) {
        this.sense = sense;
        this.score = score;
    }

    public @NotNull String getSense() {
        return sense;
    }

    public double getScore() {
        return score;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        ScoredSense that = (ScoredSense) o;
        return Double.compare(that.score, score) == 0 &&
                sense.equals(that.sense);
    }

    @Override
    public int hashCode() {
        return Objects.hash(sense, score);
    }

    @Override
    public String toString() {
        return "ScoredSense{" +
                "sense='" + sense + '\'' +
                ", score=" + score +
                '}';
    }
}
