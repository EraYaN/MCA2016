big_data = [
(0.666666667)
(0.661453242)
(0.333333333)
(0.342619746)
(0.426849137)
(0.477493832)
(0.463343109)
];
small_data = [
[0.666666667]
[nan]
[0.442748092]
[0.632315522]
[0.333333333]
[0.384223919]
[0.435114504]
];


bar(big_data')
xticklabel_rotate([1:7],45,{'Combined','Two-level','Std. Neural','F.P. Neural','gshare','bi-mode','YAGS'},'interpreter','none')
matlab2tikz('norm-perf-big-predictors.tikz', 'height', '\figureheight', 'width', '\figurewidth');
figure()
bar(small_data')
xticklabel_rotate([1:7],45,{'Combined','Two-level','Std. Neural','F.P. Neural','gshare','bi-mode','YAGS'},'interpreter','none')
matlab2tikz('norm-perf-small-predictors.tikz', 'height', '\figureheight', 'width', '\figurewidth');