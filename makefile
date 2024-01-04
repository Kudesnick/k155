INDEX=index.html
PY=python.exe

all: chipinfo/$(INDEX) microshemca/$(INDEX)

chipinfo/$(INDEX): kiloom/$(INDEX)
	cd $(dir $@) && $(PY) ../$(dir $@)_scrap.py

kiloom/$(INDEX):
	cd $(dir $@) && $(PY) ../$(dir $@)_scrap.py

microshemca/$(INDEX):
	cd $(dir $@) && $(PY) ../$(dir $@)_scrap.py

clear:
	rm $(addsuffix /*.html, chipinfo kiloom microshemca)
