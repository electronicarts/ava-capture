CXX=g++
SOURCES=ximeaTest.cpp
OBJECTS=$(SOURCES:.cpp=.o)
PROGRAM=ximeaTest

all: $(PROGRAM)

$(PROGRAM): $(OBJECTS)
	$(CXX) -g $(OBJECTS) -o $@ -lm3api

.cpp.o: $(patsubst %.cpp,%.o,$(wildcard *.cpp))
	$(CXX) -g -c $< -o $@

clean:
	rm -f $(PROGRAM) $(OBJECTS)

install:
	cp $(PROGRAM) ../../bin
