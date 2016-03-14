package edu.umn.biomedicus.common.terms;

import javax.annotation.Nullable;

/**
 *
 */
public class IndexedTerm implements Comparable<IndexedTerm> {
    private final int termIdentifier;

    IndexedTerm(int termIdentifier) {
        this.termIdentifier = termIdentifier;
    }

    int termIdentifier() {
        return termIdentifier;
    }

    @Override
    public boolean equals(@Nullable Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        IndexedTerm that = (IndexedTerm) o;

        return termIdentifier == that.termIdentifier;

    }

    @Override
    public int hashCode() {
        return termIdentifier;
    }

    @Override
    public int compareTo(IndexedTerm o) {
        return Integer.compare(termIdentifier, o.termIdentifier);
    }
}
