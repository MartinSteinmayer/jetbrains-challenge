package org.mycopilot.mycopilot

import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.Messages
import java.io.*

class PopUpChat : AnAction() {

    fun loadEnv(filePath: String): Map<String, String> {
        val envMap = mutableMapOf<String, String>()
        File(filePath).forEachLine { line ->
            if (line.isNotBlank() && !line.startsWith("#")) {
                val (key, value) = line.split("=", limit = 2)
                envMap[key.trim()] = value.trim()
            }
        }
        return envMap
    }

    override fun actionPerformed(event: AnActionEvent) {
        val project: Project? = event.project
        val title = "Chat with Copilot"

        // Ask for user input
        val userInput = Messages.showInputDialog(project, "Enter your message:", title, Messages.getQuestionIcon())
        if (userInput.isNullOrBlank()) {
            Messages.showErrorDialog(project, "No input provided. Chat cannot start.", title)
            return
        }

        // Run the Python script with the user input
        val processBuilder = ProcessBuilder(
                "/home/martinjs/Documents/fullstack-projects/hackatum/jetbrains/venv/bin/python3",
                "/home/martinjs/Documents/fullstack-projects/hackatum/jetbrains/main.py",
                userInput
        )

        val env = loadEnv("/home/martinjs/Documents/fullstack-projects/hackatum/jetbrains/myCopilot/src/main/kotlin/org/mycopilot/mycopilot/.env")
        val openAiApiKey = env["OPENAI_API_KEY"]

        val environment = processBuilder.environment()
        environment["OPENAI_API_KEY"] = openAiApiKey

        processBuilder.redirectErrorStream(true)

        try {
            println("Starting chatbot process with input: $userInput")
            val process = processBuilder.start()
            println("Process started: ${process.isAlive}")

            val reader = BufferedReader(InputStreamReader(process.inputStream))
            val response = StringBuilder()

            // Read the output from the Python process
            // Read the output line by line and append it to the response
            reader.forEachLine { line ->
                println("Chatbot output: $line")
                response.append(line).append("\n")
            }

            // Wait for the process to finish
            val exitCode = process.waitFor()
            println("Process exited with code: $exitCode")

            if (exitCode != 0) {
                throw IOException("Chatbot process exited with non-zero exit code: $exitCode.")
            }

            // Show the response in a popup dialog
            Messages.showMessageDialog(project, response.toString().trim(), title, Messages.getInformationIcon())

        } catch (ex: Exception) {
            Messages.showErrorDialog(project, "Failed to communicate with the chatbot: ${ex.message}", title)
            ex.printStackTrace()
        }
    }

    override fun update(e: AnActionEvent) {
        val project = e.project
        e.presentation.isEnabledAndVisible = project != null
    }

    override fun getActionUpdateThread(): ActionUpdateThread {
        return ActionUpdateThread.BGT
    }
}
