#!/bin/bash
pkill -f "bld\.sh"; pkill -x cmake; pkill -x ninja; sleep 1; pkill -x nvcc; pkill -x cicc; pkill -x ptxas; pkill -x ccache; pkill -x cc1plus; sleep 2; echo left=$(pgrep -xc "cicc|ptxas|nvcc|ninja|cmake|cc1plus")
