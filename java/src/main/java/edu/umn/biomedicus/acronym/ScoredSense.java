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
