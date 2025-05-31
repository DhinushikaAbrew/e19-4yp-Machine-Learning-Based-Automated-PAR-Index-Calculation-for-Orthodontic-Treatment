package com.orthodontics.filemanagement.service;

import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.Objects;
import java.util.zip.GZIPInputStream;

public class FileUtils {

    public static File extractGzFile(MultipartFile gzFile, String outputDir) throws IOException {
        if (Objects.requireNonNull(gzFile.getOriginalFilename()).endsWith(".stl")){
            File extractedFile = new File(outputDir, gzFile.getOriginalFilename());
            try (FileOutputStream fileOutputStream = new FileOutputStream(extractedFile)) {
                fileOutputStream.write(gzFile.getBytes());
            }
            return extractedFile;
        }

        File extractedFile = new File(outputDir, gzFile.getOriginalFilename().replace(".gz", ""));
        try (GZIPInputStream gzipInputStream = new GZIPInputStream(gzFile.getInputStream());
             FileOutputStream fileOutputStream = new FileOutputStream(extractedFile)) {
            byte[] buffer = new byte[1024];
            int len;
            while ((len = gzipInputStream.read(buffer)) > 0) {
                fileOutputStream.write(buffer, 0, len);
            }
        }
        return extractedFile;
    }
}
