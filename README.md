# KTH Course Scraper

A simple scraper for information about all courses given at [KTH Royal Institute of Technology](https://www.kth.se/en). The creation of this scraper had no real purpose other than wasting some time. It is made available just in case someone else might find it useful.

Running the scraper requires Python 3.8 or later (*due to the use of built-in type annotations*), an installation of [Firefox](https://www.mozilla.org), and the packages listed in [requirements.txt](requirements.txt).

The scraper is run by executing [scraper.py](scraper.py) which will create two files, [kth_courses.csv](kth_courses.csv) and [kth_offerings.csv](kth_offerings.csv). The first file contains information about all courses, while the second file contains information about all offerings of courses. The two files can be combined through an inner join on the `Course code` column, which is the primary key for the `kth_courses.csv` file, while joint primary keys for the `kth_offerings.csv` file are `Course code` and `Semester`.

For testing purposes, the scraper can be run with the `--debug` flag set to `True`, which will limit the scraping to the first `20` courses.
