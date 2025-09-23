#include "note_fft.hpp"

#define com_d complex<double> // I got tired of typing complex<double> so I only left it in the function declarations 

namespace FFT
{
    // TODO: add NULL checks
    // TODO: either change to templates or overload to work with integers/floats

    const complex<double> n_2pi_i = complex<double>(0, -2 * PI);

    /*Main FFT function (Cooley-Tukey implementation).
    * 
    - Returns complex array, same size as the original.

    - For spectrum graphing or any other uses, use complex_magnitude() to convert 
    the complex array into an array of float magnitude values.

    - For frequency scaling, use index_to_frequency() function.

    - Note, the resulting array is mirrored, meaning that the values at the 
    kth index are the same as the ones at the n-k index.*/
    complex<double>* fft(double* arr, int n_samples)
    {
        //int n_samples = sizeof(arr) / sizeof(arr[0]);
        // A power of two will only have one bit followed by zeroes. Applying a bitand mask with the number just before it results in zero exclusively for powers of 2
        if (arr == nullptr) { throw new exception("Cannot pass null pointer."); }
        bool n_samples_power_of_two = !(n_samples == 0) && !(n_samples & (n_samples - 1)); 
        if (!n_samples_power_of_two) { throw new std::exception("The input array must be a power of two."); }

        com_d* comp_arr = (com_d*)malloc(sizeof(com_d)*n_samples);
        for (int i = 0; i < n_samples; i++) { comp_arr[i] = com_d(arr[i]); };

        return _fft(comp_arr, n_samples);
    }

    /*Recursive component of fft function.
    * 
    - Works by constantly splitting the initial array into halves, 
    making use of complex number symmetry to reduce the time complexity
    from O(n) to O(log(n)) (for the exponent calculations).

    -  Overall, it works in O(nlog(n)).*/
    complex<double>* _fft(complex<double>* arr, int n_samples) 
    {
        int half_n = n_samples / 2;
        if(n_samples==1){return arr;} // End condition for recursion

        com_d n = com_d(n_samples);
        com_d* arr_e = (com_d*)malloc(sizeof(arr[0])*half_n);
        com_d* arr_o = (com_d*)malloc(sizeof(arr[0])*half_n);

        // Split current array into an array for even indexes, and one for odd ones
        for(int i=0; i<n_samples; i++){         
            if (i % 2)  {arr_o[i/2] = arr[i];}
            else        {arr_e[i/2] = arr[i];}
        }

        // Recursive call to get coefficients from newly created arrays 
        com_d* y_e = _fft(arr_e, half_n);
        com_d* y_o = _fft(arr_o, half_n);
        
        com_d factor;
        for(int k=0; k<half_n;k++){
            factor = exp(com_d(k)*n_2pi_i / n) * y_o[k]; // e^(-2PI*i*k/N) * odd-array value
            arr[k] = y_e[k] + factor;
            arr[k + half_n] = y_e[k] - factor;
        }

        free(y_o);
        free(y_e);
        return arr; // TODO: sort out memory allocation
    }

    complex<double>* fft_better(complex<double>* arr, complex<double>* arr2, int n_samples);

    complex<double>* _fft_better(complex<double>* arr, complex<double>* arr2, int n_samples)
    {
        int half_n = n_samples / 2;
        if (n_samples == 1) { return arr; } // End condition for recursion
        com_d n = com_d(n_samples);
        com_d factor;


        for (int k = 0; k < half_n; k++) {
            factor = exp(com_d(k) * n_2pi_i / n) * y_o[k]; // e^(-2PI*i*k/N) * odd-array value
            arr[k] = y_e[k] + factor;
            arr[k + half_n] = y_e[k] - factor;
        }

        free(y_o);
        free(y_e);
        return arr; // TODO: sort out memory allocation
    }

    // Returns pointer to a new array of magnitude values from a passed array of complex numbers.
    double* complex_magnitude(complex<double>* arr, int n_samples)
    {
        double* output_array = (double*)malloc(sizeof(double) * n_samples);
        for(int i=0; i<n_samples; i++){output_array[i] = abs(arr[i]);}
        return output_array;
    }



    // Returns the corresponding frequency to the kth element in any FFT array from this namespace
    float index_to_frequency(int k, int n_samples, int bitrate) {return static_cast<float>(k * bitrate) / n_samples; }

    // Intended for use after applying complex_magnitude() function
    float get_peak_frequency(double* arr, int n_samples, int bitrate){return index_to_frequency(get_peak_index(arr, n_samples), n_samples, bitrate);}

    // Intended for use after applying complex_magnitude() function
    int get_peak_index(double* arr, int n_samples)
    {
        double peak = arr[0];
        int index = 0;
        for (int i = 1; i < n_samples; i++)
        {
            if (arr[i] > peak)
            {
                peak = arr[i];
                index = i;
            }
        }
        return index;
    }

    void high_freq_cutoff(double* arr, int n_samples, double decay_const)
    {
        for (int i = 1; i < n_samples; i++) {arr[i] *= exp(static_cast<double>(i) * decay_const);}
    }

    void kernel(){}

    double* gaussian_kernel(double* arr, int n_samples, int n_neighbours, double sigma)
    {
        if (n_samples==0) { throw new exception("Cannot take arrays of size 0."); }
        int n_bytes = sizeof(double) * n_samples;
        double* new_arr = (double*)malloc(n_bytes);


        double weight;
        double new_value;
        double normalisation_factor;
        for(int i=0; i<n_samples; i++)
        {
            normalisation_factor = 0;
            weight = 0;
            new_value = 0;
            for (int j = -n_neighbours; j <= n_neighbours; j++)
            {
                if(i+j>=0 && i+j<n_samples)
                {
                    weight = exp(-pow(abs(arr[i] - arr[i + j]), 2) / (2 * pow(sigma, 2)));
                    new_value += arr[i + j] * weight;
                    normalisation_factor += weight;
                }
            }
            if (normalisation_factor != 0) { new_arr[i] = new_value / normalisation_factor; }
            else { new_arr[i] = 0; }
        }
        return new_arr;
    }
}