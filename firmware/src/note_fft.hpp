#pragma once

#include <iostream>
#include <complex>
#include <cmath>
#include <vector>
#include <typeinfo>
#include <memory>

using namespace std;

namespace FFT{
	complex<double>* fft(const double arr[]);
	complex<double>* _fft(complex<double>* arr, int n_samples);
	double* complex_magnitude(complex<double>* arr, int n_samples);

	float index_to_frequency(int k, int n_samples, int bitrate);
	
	float get_peak_frequency(double* arr, int n_samples, int bitrate);
	int get_peak_index(double* arr, int n_samples);
};
