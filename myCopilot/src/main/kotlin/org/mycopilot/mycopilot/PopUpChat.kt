package org.mycopilot.mycopilot

import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.project.Project
import java.awt.BorderLayout
import java.awt.Dimension
import javax.swing.*
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

        // Create a chat window
        val chatFrame = JFrame(title)
        chatFrame.defaultCloseOperation = JFrame.DISPOSE_ON_CLOSE
        chatFrame.layout = BorderLayout()
        chatFrame.setSize(500, 400)
        chatFrame.minimumSize = Dimension(400, 300)

        // Chat history panel
        val chatArea = JTextArea()
        chatArea.isEditable = false
        val scrollPane = JScrollPane(chatArea)
        chatFrame.add(scrollPane, BorderLayout.CENTER)

        // User input panel
        val inputPanel = JPanel(BorderLayout())
        val userInputField = JTextField()
        val sendButton = JButton("Send")
        inputPanel.add(userInputField, BorderLayout.CENTER)
        inputPanel.add(sendButton, BorderLayout.EAST)
        chatFrame.add(inputPanel, BorderLayout.SOUTH)

        chatFrame.isVisible = true
        

        val messageList = mutableListOf<String>()
        // Add action listener for the send button
        sendButton.addActionListener {
            val userInput = userInputField.text.trim()
            if (userInput.isNotEmpty()) {
                chatArea.append("You: $userInput\n")
                userInputField.text = ""

                // Create message list 
                messageList.add("You: $userInput\n")


                // Process user input in the background
                processChatInput(messageList, chatArea)
            }
        }
    }

    private fun processChatInput(messageList: MutableList<String>, chatArea: JTextArea) {

        val tempFile = File.createTempFile("chat_history", ".txt")
        tempFile.writeText(messageList.joinToString("\n"))

        val processBuilder = ProcessBuilder(
                "/home/martinjs/Documents/fullstack-projects/hackatum/jetbrains/venv/bin/python3",
                "/home/martinjs/Documents/fullstack-projects/hackatum/jetbrains/main.py",
                tempFile.absolutePath
        )

        // Load environment variables
        val env = loadEnv("/home/martinjs/Documents/fullstack-projects/hackatum/jetbrains/myCopilot/src/main/kotlin/org/mycopilot/mycopilot/.env")
        val openAiApiKey = env["OPENAI_API_KEY"]
        val environment = processBuilder.environment()
        environment["OPENAI_API_KEY"] = openAiApiKey

        processBuilder.redirectErrorStream(true)

        // Use SwingWorker for non-blocking execution
        val worker = object : SwingWorker<String, Void>() {
            override fun doInBackground(): String {
                return try {
                    val process = processBuilder.start()
                    val reader = BufferedReader(InputStreamReader(process.inputStream))
                    val response = StringBuilder()

                    // Read the output line by line
                    reader.forEachLine { line ->
                        response.append(line).append("\n")
                    }

                    val exitCode = process.waitFor()
                    if (exitCode != 0) {
                        throw IOException("Chatbot process exited with code $exitCode.")
                    }

                    response.toString().trim()
                } catch (ex: Exception) {
                    ex.printStackTrace()
                    "Error: ${ex.message}"
                }
            }

            override fun done() {
                try {
                    // Append the chatbot's response to the chat area
                    val response = get()
                    chatArea.append("Copilot: $response\n")
                    messageList.add("Copilot: $response\n")
                } catch (ex: Exception) {
                    chatArea.append("Error communicating with chatbot: ${ex.message}\n")
                    messageList.add("Copilot: Error communicating with chatbot: ${ex.message}\n")
                }
            }
        }

        // Start the worker
        chatArea.append("Copilot: Thinking...\n")
        worker.execute()
    }

    override fun update(e: AnActionEvent) {
        val project = e.project
        e.presentation.isEnabledAndVisible = project != null
    }

    override fun getActionUpdateThread(): ActionUpdateThread {
        return ActionUpdateThread.BGT
    }
}
