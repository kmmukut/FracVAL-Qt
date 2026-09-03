# FracVAL build
# Compiler-generated Fortran files stay in build/. The optional Python F2PY
# extension is written into python/fracval/ and can be removed with make clean.

FC = gfortran
FFLAGS ?= -O2
LDFLAGS ?=
PYTHON ?= python3

SRC_DIR := src
BUILD_DIR := build
TARGET := $(BUILD_DIR)/fracval

OBJECTS := \
	$(BUILD_DIR)/Ctes.o \
	$(BUILD_DIR)/random.o \
	$(BUILD_DIR)/RAND_SAMPLE.o \
	$(BUILD_DIR)/a_Random_PP.o \
	$(BUILD_DIR)/PCA_cca.o \
	$(BUILD_DIR)/PCA_Subclusters_module.o \
	$(BUILD_DIR)/Save_results_CC.o \
	$(BUILD_DIR)/CCA_module.o \
	$(BUILD_DIR)/Frac_VAL_CCA.o

.PHONY: all run install install-gui info test fortran-test python-ext python-test gui qt-check gui-test plot-test docs docs-clean debug clean help

all: $(TARGET)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/%.o: $(SRC_DIR)/%.f90 | $(BUILD_DIR)
	$(FC) $(FFLAGS) -J$(BUILD_DIR) -I$(BUILD_DIR) -c $< -o $@

$(BUILD_DIR)/a_Random_PP.o: $(BUILD_DIR)/random.o
$(BUILD_DIR)/PCA_Subclusters_module.o: $(BUILD_DIR)/PCA_cca.o
$(BUILD_DIR)/CCA_module.o: $(BUILD_DIR)/Ctes.o $(BUILD_DIR)/PCA_Subclusters_module.o $(BUILD_DIR)/Save_results_CC.o
$(BUILD_DIR)/Frac_VAL_CCA.o: $(BUILD_DIR)/Ctes.o $(BUILD_DIR)/a_Random_PP.o $(BUILD_DIR)/RAND_SAMPLE.o $(BUILD_DIR)/CCA_module.o

$(TARGET): $(OBJECTS)
	$(FC) $(FFLAGS) $(OBJECTS) $(LDFLAGS) -o $@

run: $(TARGET)
	$(TARGET) $(if $(INPUT),$(INPUT),fracval.in)

install:
	$(PYTHON) -m pip install -e .
	$(MAKE) python-ext PYTHON=$(PYTHON)

install-gui:
	$(PYTHON) -m pip install -e '.[gui]'
	$(MAKE) python-ext PYTHON=$(PYTHON)

info:
	PYTHONPATH=python $(PYTHON) -m fracval.diagnostics

fortran-test: $(TARGET)
	bash tests/run_tests.sh $(TARGET)

python-ext:
	FC=$(FC) $(PYTHON) python/build_fortran_extension.py

python-test: $(TARGET) python-ext
	PYTHONPATH=python $(PYTHON) tests/python/test_qt_runtime_paths.py
	PYTHONPATH=python $(PYTHON) tests/python/test_python_api.py
	PYTHONPATH=python $(PYTHON) tests/python/test_visualization.py

test: fortran-test python-test

gui: $(TARGET)
	@PYTHONPATH=python $(PYTHON) -c "import PySide6; from PySide6.QtWebEngineWidgets import QWebEngineView" >/dev/null 2>&1 || \
		( echo "PySide6 is missing. Install with: $(PYTHON) -m pip install -e '.[gui]'"; exit 1 )
	PYTHONPATH=python $(PYTHON) gui/app.py

qt-check:
	PYTHONPATH=python $(PYTHON) -m fracval.desktop.qt_runtime

gui-test:
	PYTHONPATH=python QTWEBENGINE_DISABLE_SANDBOX=1 QTWEBENGINE_CHROMIUM_FLAGS='--disable-gpu --no-sandbox' $(PYTHON) tests/python/test_qt_gui.py

docs:
	mkdir -p $(BUILD_DIR)/docs
	cd doc && latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=../$(BUILD_DIR)/docs FracVAL_User_Developer_Guide.tex
	cp $(BUILD_DIR)/docs/FracVAL_User_Developer_Guide.pdf doc/FracVAL_User_Developer_Guide.pdf


docs-clean:
	rm -rf $(BUILD_DIR)/docs

plot-test: fortran-test
	$(PYTHON) plot/plot_aggregate.py tests/monodisperse/results/N_00000100_Agg_00000001.dat \
		--backend matplotlib --output build/monodisperse.png
	$(PYTHON) plot/plot_aggregate.py tests/polydisperse/results/N_00000100_Agg_00000001.dat \
		--backend plotly --mode centers --output build/polydisperse.html
	@echo "Plot smoke tests written to build/monodisperse.png and build/polydisperse.html"

debug:
	$(MAKE) clean
	$(MAKE) FFLAGS='-O0 -g -Wall -Wextra -fcheck=all -fbacktrace' all

clean:
	rm -f $(BUILD_DIR)/*.o $(BUILD_DIR)/*.mod $(TARGET) \
		$(BUILD_DIR)/*.png $(BUILD_DIR)/*.html
	rm -rf $(BUILD_DIR)/python_ext
	rm -f python/fracval/_fracval_fortran*.so python/fracval/_fracval_fortran*.dylib python/fracval/_fracval_fortran*.pyd
	@touch $(BUILD_DIR)/.gitkeep 2>/dev/null || true

help:
	@echo "FracVAL targets:"
	@echo "  make              Build build/fracval"
	@echo "  make run          Run using ./fracval.in"
	@echo "  make install      Install editable Python package + F2PY extension"
	@echo "  make install-gui  Install editable package with PySide6 + extension"
	@echo "  make info         Show Python/backend diagnostics"
	@echo "  make run INPUT=x  Run using input file x"
	@echo "  make fortran-test Run mono/polydisperse standalone smoke tests"
	@echo "  make python-ext   Build the in-memory Python/Fortran extension"
	@echo "  make python-test  Test Python API + extension + visualization"
	@echo "  make test         Run Fortran and Python tests"
	@echo "  make gui          Launch the native PySide6/Qt desktop GUI"
	@echo "  make qt-check     Show PySide6/Qt plugin paths and available platforms"
	@echo "  make gui-test     Smoke-test Qt GUI construction (requires PySide6)"
	@echo "  make plot-test    Test static and interactive file plotting"
	@echo "  make docs         Build the LaTeX user/developer manual PDF"
	@echo "  make docs-clean   Remove LaTeX build intermediates"
	@echo "  make debug        Rebuild standalone generator with runtime checks"
	@echo "  make clean        Remove compiler-generated files"
