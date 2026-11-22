"""Independent word-error scorer; evaluates speech text, never ASL quality."""
from .translation import normalize

def word_errors(reference,hypothesis):
    ref=normalize(reference).split();hyp=normalize(hypothesis).split()
    if not ref:raise ValueError('Reference must contain words')
    if len(ref)*len(hyp)>4_000_000:raise ValueError('Score shorter passages separately')
    # Tuple: total edit cost, substitutions, deletions, insertions.
    previous=[(j,0,0,j) for j in range(len(hyp)+1)]
    for i,word in enumerate(ref,1):
        current=[(i,0,i,0)]
        for j,predicted in enumerate(hyp,1):
            if word==predicted:current.append(previous[j-1]);continue
            cost,s,d,ins=previous[j-1];substitution=(cost+1,s+1,d,ins)
            cost,s,d,ins=previous[j];deletion=(cost+1,s,d+1,ins)
            cost,s,d,ins=current[-1];insertion=(cost+1,s,d,ins+1)
            current.append(min([substitution,deletion,insertion],key=lambda x:x[0]))
        previous=current
    errors,substitutions,deletions,insertions=previous[-1]
    return {'reference_words':len(ref),'hypothesis_words':len(hyp),'errors':errors,'substitutions':substitutions,
            'deletions':deletions,'insertions':insertions,'wer_percent':100*errors/len(ref),
            'normalization':'Project NFKC/lowercase word tokenizer, punctuation ignored; contractions retained',
            'scope':'Speech recognition text only; not ASL correctness or comprehension'}
