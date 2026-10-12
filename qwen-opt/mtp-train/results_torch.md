## Shipped MTP head, llama.cpp draft chain (n_draft=4)

### en (resp tokens outside 64k draft vocab: 2.0%) (n=35279 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.785 | 0.581 | 0.427 | 0.315 | 0.785 | 0.741 | 0.734 | 0.739 | 3.11 |
| shipped, expected | 0.784 | 0.581 | 0.428 | 0.315 | 0.784 | 0.741 | 0.736 | 0.737 | 3.11 |
| shipped, T=0 agreement | 0.824 | 0.600 | 0.438 | 0.320 | 0.824 | 0.728 | 0.730 | 0.731 | 3.18 |
| oracle greedy (target argmax) | 0.870 | 0.767 | 0.683 | 0.611 | 0.870 | 0.882 | 0.890 | 0.895 | 3.93 |

### pl (resp tokens outside 64k draft vocab: 3.7%) (n=33757 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.773 | 0.548 | 0.382 | 0.270 | 0.773 | 0.710 | 0.696 | 0.709 | 2.97 |
| shipped, expected | 0.771 | 0.548 | 0.382 | 0.271 | 0.771 | 0.711 | 0.698 | 0.708 | 2.97 |
| shipped, T=0 agreement | 0.808 | 0.564 | 0.391 | 0.276 | 0.808 | 0.697 | 0.693 | 0.706 | 3.04 |
| oracle greedy (target argmax) | 0.872 | 0.768 | 0.678 | 0.602 | 0.872 | 0.880 | 0.883 | 0.887 | 3.92 |

### all (resp tokens outside 64k draft vocab: 2.8%) (n=69036 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.779 | 0.565 | 0.405 | 0.293 | 0.779 | 0.726 | 0.716 | 0.725 | 3.04 |
| shipped, expected | 0.777 | 0.565 | 0.405 | 0.293 | 0.777 | 0.727 | 0.718 | 0.724 | 3.04 |
| shipped, T=0 agreement | 0.817 | 0.582 | 0.415 | 0.299 | 0.817 | 0.713 | 0.713 | 0.719 | 3.11 |
| oracle greedy (target argmax) | 0.871 | 0.768 | 0.680 | 0.606 | 0.871 | 0.881 | 0.886 | 0.891 | 3.93 |

### en-chat (resp tokens outside 64k draft vocab: 2.3%) (n=8736 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.716 | 0.473 | 0.305 | 0.191 | 0.716 | 0.661 | 0.645 | 0.626 | 2.68 |
| shipped, expected | 0.716 | 0.475 | 0.307 | 0.194 | 0.716 | 0.664 | 0.647 | 0.629 | 2.69 |
| shipped, T=0 agreement | 0.772 | 0.502 | 0.322 | 0.199 | 0.772 | 0.651 | 0.641 | 0.618 | 2.79 |
| oracle greedy (target argmax) | 0.823 | 0.683 | 0.572 | 0.479 | 0.823 | 0.831 | 0.836 | 0.837 | 3.56 |

### en-code (resp tokens outside 64k draft vocab: 1.5%) (n=10502 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.885 | 0.752 | 0.619 | 0.507 | 0.885 | 0.850 | 0.823 | 0.819 | 3.76 |
| shipped, expected | 0.883 | 0.749 | 0.620 | 0.505 | 0.883 | 0.849 | 0.827 | 0.815 | 3.76 |
| shipped, T=0 agreement | 0.905 | 0.762 | 0.629 | 0.510 | 0.905 | 0.842 | 0.826 | 0.810 | 3.81 |
| oracle greedy (target argmax) | 0.935 | 0.883 | 0.836 | 0.794 | 0.935 | 0.944 | 0.947 | 0.949 | 4.45 |

### en-tech (resp tokens outside 64k draft vocab: 1.6%) (n=8275 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.822 | 0.634 | 0.482 | 0.363 | 0.822 | 0.771 | 0.760 | 0.753 | 3.30 |
| shipped, expected | 0.821 | 0.635 | 0.483 | 0.363 | 0.821 | 0.774 | 0.760 | 0.752 | 3.30 |
| shipped, T=0 agreement | 0.854 | 0.651 | 0.492 | 0.368 | 0.854 | 0.763 | 0.756 | 0.747 | 3.36 |
| oracle greedy (target argmax) | 0.894 | 0.804 | 0.729 | 0.663 | 0.894 | 0.900 | 0.907 | 0.910 | 4.09 |

### pl-chat (resp tokens outside 64k draft vocab: 3.5%) (n=11255 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.771 | 0.543 | 0.375 | 0.264 | 0.771 | 0.705 | 0.691 | 0.703 | 2.95 |
| shipped, expected | 0.765 | 0.541 | 0.376 | 0.264 | 0.765 | 0.707 | 0.695 | 0.703 | 2.95 |
| shipped, T=0 agreement | 0.808 | 0.558 | 0.386 | 0.271 | 0.808 | 0.691 | 0.691 | 0.702 | 3.02 |
| oracle greedy (target argmax) | 0.867 | 0.758 | 0.663 | 0.583 | 0.867 | 0.874 | 0.875 | 0.878 | 3.87 |

### pl-code (resp tokens outside 64k draft vocab: 2.7%) (n=6985 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.855 | 0.694 | 0.560 | 0.450 | 0.855 | 0.812 | 0.806 | 0.804 | 3.56 |
| shipped, expected | 0.857 | 0.697 | 0.560 | 0.450 | 0.857 | 0.813 | 0.804 | 0.804 | 3.56 |
| shipped, T=0 agreement | 0.883 | 0.709 | 0.569 | 0.457 | 0.883 | 0.802 | 0.802 | 0.804 | 3.62 |
| oracle greedy (target argmax) | 0.922 | 0.856 | 0.798 | 0.746 | 0.922 | 0.929 | 0.932 | 0.935 | 4.32 |

### pl-tech (resp tokens outside 64k draft vocab: 3.0%) (n=5574 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.816 | 0.609 | 0.431 | 0.306 | 0.816 | 0.746 | 0.709 | 0.710 | 3.16 |
| shipped, expected | 0.811 | 0.610 | 0.436 | 0.308 | 0.811 | 0.752 | 0.716 | 0.706 | 3.16 |
| shipped, T=0 agreement | 0.844 | 0.626 | 0.444 | 0.312 | 0.844 | 0.742 | 0.709 | 0.703 | 3.23 |
| oracle greedy (target argmax) | 0.900 | 0.817 | 0.744 | 0.679 | 0.900 | 0.908 | 0.910 | 0.913 | 4.14 |

### en-prose (resp tokens outside 64k draft vocab: 2.9%) (n=7766 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.686 | 0.415 | 0.244 | 0.145 | 0.686 | 0.606 | 0.588 | 0.594 | 2.49 |
| shipped, expected | 0.687 | 0.415 | 0.243 | 0.144 | 0.687 | 0.603 | 0.587 | 0.592 | 2.49 |
| shipped, T=0 agreement | 0.743 | 0.437 | 0.254 | 0.150 | 0.743 | 0.588 | 0.581 | 0.591 | 2.58 |
| oracle greedy (target argmax) | 0.811 | 0.667 | 0.550 | 0.457 | 0.811 | 0.822 | 0.826 | 0.831 | 3.49 |

### en-think (resp tokens outside 64k draft vocab: 1.9%) (n=11700 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.779 | 0.568 | 0.408 | 0.291 | 0.779 | 0.729 | 0.719 | 0.712 | 3.05 |
| shipped, expected | 0.774 | 0.568 | 0.408 | 0.292 | 0.774 | 0.733 | 0.718 | 0.715 | 3.04 |
| shipped, T=0 agreement | 0.819 | 0.591 | 0.421 | 0.296 | 0.819 | 0.722 | 0.712 | 0.704 | 3.13 |
| oracle greedy (target argmax) | 0.861 | 0.755 | 0.665 | 0.587 | 0.861 | 0.877 | 0.881 | 0.882 | 3.87 |

### pl-prose (resp tokens outside 64k draft vocab: 5.0%) (n=9943 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.693 | 0.418 | 0.236 | 0.132 | 0.693 | 0.603 | 0.564 | 0.558 | 2.48 |
| shipped, expected | 0.693 | 0.417 | 0.235 | 0.131 | 0.693 | 0.602 | 0.563 | 0.558 | 2.48 |
| shipped, T=0 agreement | 0.736 | 0.433 | 0.242 | 0.134 | 0.736 | 0.589 | 0.558 | 0.555 | 2.54 |
| oracle greedy (target argmax) | 0.828 | 0.690 | 0.574 | 0.478 | 0.828 | 0.833 | 0.832 | 0.833 | 3.57 |

### pl-think (resp tokens outside 64k draft vocab: 2.1%) (n=9990 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.807 | 0.614 | 0.462 | 0.342 | 0.807 | 0.761 | 0.753 | 0.741 | 3.23 |
| shipped, expected | 0.802 | 0.612 | 0.460 | 0.342 | 0.802 | 0.763 | 0.753 | 0.742 | 3.22 |
| shipped, T=0 agreement | 0.843 | 0.631 | 0.472 | 0.349 | 0.843 | 0.748 | 0.749 | 0.740 | 3.29 |
| oracle greedy (target argmax) | 0.878 | 0.784 | 0.703 | 0.632 | 0.878 | 0.893 | 0.896 | 0.899 | 4.00 |

### en-answer (resp tokens outside 64k draft vocab: 2.1%) (n=23579 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.787 | 0.588 | 0.436 | 0.327 | 0.787 | 0.746 | 0.741 | 0.751 | 3.14 |
| shipped, expected | 0.789 | 0.588 | 0.437 | 0.327 | 0.789 | 0.745 | 0.744 | 0.747 | 3.14 |
| shipped, T=0 agreement | 0.827 | 0.605 | 0.447 | 0.332 | 0.827 | 0.731 | 0.739 | 0.743 | 3.21 |
| oracle greedy (target argmax) | 0.875 | 0.774 | 0.692 | 0.623 | 0.875 | 0.884 | 0.894 | 0.901 | 3.96 |

### pl-answer (resp tokens outside 64k draft vocab: 4.3%) (n=23767 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.758 | 0.521 | 0.348 | 0.240 | 0.758 | 0.687 | 0.667 | 0.691 | 2.87 |
| shipped, expected | 0.758 | 0.521 | 0.350 | 0.241 | 0.758 | 0.688 | 0.671 | 0.689 | 2.87 |
| shipped, T=0 agreement | 0.794 | 0.535 | 0.356 | 0.245 | 0.794 | 0.675 | 0.666 | 0.687 | 2.93 |
| oracle greedy (target argmax) | 0.870 | 0.761 | 0.668 | 0.589 | 0.870 | 0.875 | 0.877 | 0.882 | 3.89 |

## PyTorch mirror vs llama.cpp

```
{
 "d1_positions": 1024,
 "d1_top1_agree": 0.9873046875,
 "d1_logit_maxabs": 0.7611236572265625,
 "d1_logit_relL2": 0.01551163662225008,
 "d1_hnextn_relL2": 1.1820219159126282,
 "chain_token_agree": [
  0.9956073807562819,
  0.989769820971867,
  0.9819526926466976,
  0.9727773202132732
 ],
 "chain_prefix_agree": [
  0.9956073807562819,
  0.9890184518907047,
  0.980002022916757,
  0.9690060254020547
 ],
 "chain_n": 69207
}
```

## PyTorch mirror (fp32) acceptance incl. probabilistic estimator

### torch en (n=35279 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.785 | 0.581 | 0.427 | 0.315 | 0.785 | 0.741 | 0.734 | 0.739 | 3.11 |
| shipped, expected | 0.784 | 0.581 | 0.428 | 0.315 | 0.784 | 0.741 | 0.736 | 0.737 | 3.11 |
| shipped, T=0 agreement | 0.825 | 0.600 | 0.438 | 0.320 | 0.825 | 0.728 | 0.730 | 0.731 | 3.18 |
| shipped, per-depth sum min(p',q10) | 0.825 | 0.599 | 0.436 | 0.320 | 0.825 | 0.726 | 0.728 | 0.734 | 3.18 |
| oracle greedy (target argmax) | 0.870 | 0.767 | 0.683 | 0.611 | 0.870 | 0.882 | 0.890 | 0.895 | 3.93 |

### torch pl (n=33757 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.773 | 0.548 | 0.382 | 0.270 | 0.773 | 0.710 | 0.696 | 0.708 | 2.97 |
| shipped, expected | 0.771 | 0.548 | 0.383 | 0.271 | 0.771 | 0.711 | 0.698 | 0.708 | 2.97 |
| shipped, T=0 agreement | 0.809 | 0.564 | 0.391 | 0.276 | 0.809 | 0.697 | 0.693 | 0.705 | 3.04 |
| shipped, per-depth sum min(p',q10) | 0.804 | 0.561 | 0.389 | 0.274 | 0.804 | 0.698 | 0.693 | 0.706 | 3.03 |
| oracle greedy (target argmax) | 0.872 | 0.768 | 0.678 | 0.602 | 0.872 | 0.880 | 0.883 | 0.887 | 3.92 |

### torch all (n=69036 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.779 | 0.565 | 0.405 | 0.293 | 0.779 | 0.726 | 0.716 | 0.725 | 3.04 |
| shipped, expected | 0.778 | 0.565 | 0.406 | 0.293 | 0.778 | 0.727 | 0.718 | 0.724 | 3.04 |
| shipped, T=0 agreement | 0.817 | 0.582 | 0.415 | 0.298 | 0.817 | 0.713 | 0.713 | 0.719 | 3.11 |
| shipped, per-depth sum min(p',q10) | 0.815 | 0.581 | 0.413 | 0.298 | 0.815 | 0.712 | 0.711 | 0.721 | 3.11 |
| oracle greedy (target argmax) | 0.871 | 0.768 | 0.680 | 0.606 | 0.871 | 0.881 | 0.886 | 0.891 | 3.93 |

### torch en-chat (n=8736 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.715 | 0.473 | 0.304 | 0.191 | 0.715 | 0.661 | 0.643 | 0.628 | 2.68 |
| shipped, expected | 0.716 | 0.474 | 0.307 | 0.193 | 0.716 | 0.663 | 0.646 | 0.631 | 2.69 |
| shipped, T=0 agreement | 0.772 | 0.501 | 0.320 | 0.199 | 0.772 | 0.650 | 0.639 | 0.621 | 2.79 |
| shipped, per-depth sum min(p',q10) | 0.772 | 0.500 | 0.319 | 0.201 | 0.772 | 0.647 | 0.639 | 0.630 | 2.79 |
| oracle greedy (target argmax) | 0.823 | 0.683 | 0.572 | 0.479 | 0.823 | 0.831 | 0.836 | 0.837 | 3.56 |

### torch en-code (n=10502 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.885 | 0.752 | 0.620 | 0.508 | 0.885 | 0.849 | 0.825 | 0.820 | 3.77 |
| shipped, expected | 0.883 | 0.749 | 0.621 | 0.506 | 0.883 | 0.849 | 0.828 | 0.816 | 3.76 |
| shipped, T=0 agreement | 0.905 | 0.762 | 0.630 | 0.511 | 0.905 | 0.842 | 0.827 | 0.811 | 3.81 |
| shipped, per-depth sum min(p',q10) | 0.904 | 0.758 | 0.624 | 0.507 | 0.904 | 0.838 | 0.824 | 0.813 | 3.79 |
| oracle greedy (target argmax) | 0.935 | 0.883 | 0.836 | 0.794 | 0.935 | 0.944 | 0.947 | 0.949 | 4.45 |

### torch en-tech (n=8275 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.822 | 0.634 | 0.481 | 0.362 | 0.822 | 0.771 | 0.758 | 0.753 | 3.30 |
| shipped, expected | 0.821 | 0.636 | 0.482 | 0.362 | 0.821 | 0.774 | 0.759 | 0.751 | 3.30 |
| shipped, T=0 agreement | 0.855 | 0.651 | 0.491 | 0.367 | 0.855 | 0.762 | 0.754 | 0.747 | 3.36 |
| shipped, per-depth sum min(p',q10) | 0.857 | 0.651 | 0.490 | 0.368 | 0.857 | 0.760 | 0.753 | 0.751 | 3.37 |
| oracle greedy (target argmax) | 0.894 | 0.804 | 0.729 | 0.663 | 0.894 | 0.900 | 0.907 | 0.910 | 4.09 |

### torch pl-chat (n=11255 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.771 | 0.543 | 0.376 | 0.263 | 0.771 | 0.705 | 0.692 | 0.701 | 2.95 |
| shipped, expected | 0.766 | 0.541 | 0.376 | 0.264 | 0.766 | 0.706 | 0.695 | 0.701 | 2.95 |
| shipped, T=0 agreement | 0.809 | 0.558 | 0.386 | 0.270 | 0.809 | 0.690 | 0.693 | 0.699 | 3.02 |
| shipped, per-depth sum min(p',q10) | 0.804 | 0.559 | 0.386 | 0.269 | 0.804 | 0.695 | 0.692 | 0.696 | 3.02 |
| oracle greedy (target argmax) | 0.867 | 0.758 | 0.663 | 0.583 | 0.867 | 0.874 | 0.875 | 0.878 | 3.87 |

### torch pl-code (n=6985 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.855 | 0.694 | 0.560 | 0.450 | 0.855 | 0.811 | 0.807 | 0.804 | 3.56 |
| shipped, expected | 0.858 | 0.696 | 0.560 | 0.450 | 0.858 | 0.812 | 0.805 | 0.804 | 3.56 |
| shipped, T=0 agreement | 0.884 | 0.709 | 0.569 | 0.457 | 0.884 | 0.802 | 0.803 | 0.804 | 3.62 |
| shipped, per-depth sum min(p',q10) | 0.880 | 0.706 | 0.563 | 0.452 | 0.880 | 0.803 | 0.797 | 0.803 | 3.60 |
| oracle greedy (target argmax) | 0.922 | 0.856 | 0.798 | 0.746 | 0.922 | 0.929 | 0.932 | 0.935 | 4.32 |

### torch pl-tech (n=5574 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.816 | 0.609 | 0.432 | 0.307 | 0.816 | 0.746 | 0.710 | 0.711 | 3.16 |
| shipped, expected | 0.811 | 0.610 | 0.437 | 0.309 | 0.811 | 0.752 | 0.716 | 0.707 | 3.17 |
| shipped, T=0 agreement | 0.844 | 0.627 | 0.444 | 0.313 | 0.844 | 0.743 | 0.708 | 0.704 | 3.23 |
| shipped, per-depth sum min(p',q10) | 0.836 | 0.614 | 0.438 | 0.310 | 0.836 | 0.735 | 0.713 | 0.707 | 3.20 |
| oracle greedy (target argmax) | 0.900 | 0.817 | 0.744 | 0.679 | 0.900 | 0.908 | 0.910 | 0.913 | 4.14 |

### torch en-prose (n=7766 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.686 | 0.417 | 0.245 | 0.144 | 0.686 | 0.607 | 0.588 | 0.588 | 2.49 |
| shipped, expected | 0.687 | 0.416 | 0.244 | 0.143 | 0.687 | 0.605 | 0.587 | 0.588 | 2.49 |
| shipped, T=0 agreement | 0.743 | 0.439 | 0.255 | 0.149 | 0.743 | 0.590 | 0.580 | 0.587 | 2.59 |
| shipped, per-depth sum min(p',q10) | 0.745 | 0.442 | 0.256 | 0.150 | 0.745 | 0.593 | 0.579 | 0.584 | 2.59 |
| oracle greedy (target argmax) | 0.811 | 0.667 | 0.550 | 0.457 | 0.811 | 0.822 | 0.826 | 0.831 | 3.49 |

### torch en-think (n=11700 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.779 | 0.568 | 0.408 | 0.291 | 0.779 | 0.729 | 0.719 | 0.712 | 3.05 |
| shipped, expected | 0.774 | 0.568 | 0.408 | 0.292 | 0.774 | 0.733 | 0.718 | 0.715 | 3.04 |
| shipped, T=0 agreement | 0.819 | 0.591 | 0.421 | 0.296 | 0.819 | 0.721 | 0.712 | 0.705 | 3.13 |
| shipped, per-depth sum min(p',q10) | 0.819 | 0.588 | 0.419 | 0.298 | 0.819 | 0.717 | 0.713 | 0.711 | 3.12 |
| oracle greedy (target argmax) | 0.861 | 0.755 | 0.665 | 0.587 | 0.861 | 0.877 | 0.881 | 0.882 | 3.87 |

### torch pl-prose (n=9943 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.693 | 0.418 | 0.235 | 0.131 | 0.693 | 0.604 | 0.562 | 0.559 | 2.48 |
| shipped, expected | 0.694 | 0.417 | 0.235 | 0.131 | 0.694 | 0.602 | 0.563 | 0.559 | 2.48 |
| shipped, T=0 agreement | 0.736 | 0.433 | 0.241 | 0.134 | 0.736 | 0.588 | 0.557 | 0.554 | 2.54 |
| shipped, per-depth sum min(p',q10) | 0.733 | 0.432 | 0.242 | 0.136 | 0.733 | 0.588 | 0.560 | 0.563 | 2.54 |
| oracle greedy (target argmax) | 0.828 | 0.690 | 0.574 | 0.478 | 0.828 | 0.833 | 0.832 | 0.833 | 3.57 |

### torch pl-think (n=9990 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.807 | 0.614 | 0.464 | 0.343 | 0.807 | 0.761 | 0.755 | 0.741 | 3.23 |
| shipped, expected | 0.802 | 0.612 | 0.462 | 0.343 | 0.802 | 0.763 | 0.755 | 0.742 | 3.22 |
| shipped, T=0 agreement | 0.845 | 0.631 | 0.474 | 0.350 | 0.845 | 0.747 | 0.752 | 0.739 | 3.30 |
| shipped, per-depth sum min(p',q10) | 0.842 | 0.632 | 0.471 | 0.349 | 0.842 | 0.751 | 0.744 | 0.741 | 3.29 |
| oracle greedy (target argmax) | 0.878 | 0.784 | 0.703 | 0.632 | 0.878 | 0.893 | 0.896 | 0.899 | 4.00 |

### torch en-answer (n=23579 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.788 | 0.588 | 0.436 | 0.327 | 0.788 | 0.747 | 0.741 | 0.751 | 3.14 |
| shipped, expected | 0.789 | 0.588 | 0.437 | 0.327 | 0.789 | 0.745 | 0.744 | 0.748 | 3.14 |
| shipped, T=0 agreement | 0.827 | 0.605 | 0.447 | 0.332 | 0.827 | 0.731 | 0.739 | 0.743 | 3.21 |
| shipped, per-depth sum min(p',q10) | 0.828 | 0.605 | 0.445 | 0.331 | 0.828 | 0.730 | 0.735 | 0.744 | 3.21 |
| oracle greedy (target argmax) | 0.875 | 0.774 | 0.692 | 0.623 | 0.875 | 0.884 | 0.894 | 0.901 | 3.96 |

### torch pl-answer (n=23767 start positions)

| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |
|---|---|---|---|---|---|---|---|---|---|
| shipped, realized | 0.758 | 0.521 | 0.347 | 0.240 | 0.758 | 0.687 | 0.667 | 0.690 | 2.87 |
| shipped, expected | 0.758 | 0.521 | 0.349 | 0.241 | 0.758 | 0.688 | 0.670 | 0.689 | 2.87 |
| shipped, T=0 agreement | 0.794 | 0.536 | 0.356 | 0.244 | 0.794 | 0.675 | 0.665 | 0.687 | 2.93 |
| shipped, per-depth sum min(p',q10) | 0.788 | 0.531 | 0.354 | 0.243 | 0.788 | 0.674 | 0.667 | 0.686 | 2.92 |
| oracle greedy (target argmax) | 0.870 | 0.761 | 0.668 | 0.589 | 0.870 | 0.875 | 0.877 | 0.882 | 3.89 |
